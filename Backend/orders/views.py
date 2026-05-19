import logging
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import IntegrityError
from django.db import transaction
from django.db.models import F, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import decorators
from rest_framework import permissions, serializers, status, viewsets
from rest_framework.pagination import PageNumberPagination
from rest_framework.views import APIView
from rest_framework.response import Response

from core.throttles import AdminRateThrottle, OrderCreateRateThrottle
from core.observability import bind_context, log_event, metric_incr
from payments.models import Payment
from payments.services import RazorpayIntegrationError, create_razorpay_order
from products.models import Product
from vendors.services import create_vendor_orders_for_order
from .cart_services import clear_active_cart_items, get_active_cart_for_user, get_or_create_active_cart
from .inventory import reserve_order_inventory, release_order_inventory
from .models import Cart, CartItem, Coupon, CouponUsage, Order, OrderItem, ShippingAddress
from .tasks import send_order_email_task
from .serializers import (
    ApplyCouponSerializer,
    CartItemReadSerializer,
    CartItemWriteSerializer,
    CartSerializer,
    CouponSerializer,
    CreateOrderSerializer,
    OrderDetailSerializer,
    OrderItemSerializer,
    OrderSerializer,
    ServerCartViewSerializer,
    ShippingAddressSerializer,
)

logger = logging.getLogger(__name__)


class OrderPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class CartViewSet(viewsets.ModelViewSet):
    serializer_class = CartSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Cart.objects.filter(user=self.request.user).prefetch_related("items")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @decorators.action(detail=False, methods=["get"], url_path="active")
    def active(self, request):
        """
        Return the user's active cart with nested product details.
        Creates an empty active cart when none exists (one active cart per user).
        """
        cart = get_or_create_active_cart(request.user)
        cart = get_active_cart_for_user(request.user) or cart
        serializer = ServerCartViewSerializer(cart, context={"request": request})
        return Response(serializer.data)

    @decorators.action(detail=False, methods=["delete"], url_path="active/clear")
    def clear_active(self, request):
        """Remove all line items from the active cart."""
        clear_active_cart_items(request.user)
        return Response(status=204)


class CartItemViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["cart", "product"]

    def get_queryset(self):
        return (
            CartItem.objects.filter(cart__user=self.request.user)
            .select_related("cart", "product", "product__category")
            .prefetch_related("product__images")
        )

    def get_serializer_class(self):
        if self.action in ("list", "retrieve"):
            return CartItemReadSerializer
        return CartItemWriteSerializer

    def create(self, request, *args, **kwargs):
        write_serializer = CartItemWriteSerializer(data=request.data, context={"request": request})
        write_serializer.is_valid(raise_exception=True)
        item = write_serializer.save()
        item = self.get_queryset().get(pk=item.pk)
        read_serializer = CartItemReadSerializer(item, context={"request": request})
        return Response(read_serializer.data, status=201)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        write_serializer = CartItemWriteSerializer(
            instance,
            data=request.data,
            partial=partial,
            context={"request": request},
        )
        write_serializer.is_valid(raise_exception=True)
        item = write_serializer.save()
        item = self.get_queryset().get(pk=item.pk)
        read_serializer = CartItemReadSerializer(item, context={"request": request})
        return Response(read_serializer.data)

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)


class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = OrderPagination

    def _build_checkout_response(self, order, payment, request, created):
        serializer = OrderDetailSerializer(order, context={"request": request})
        payment_payload = {
            "payment_id": payment.id,
            "razorpay_order_id": payment.razorpay_order_id,
            "amount": payment.amount,
            "currency": payment.currency,
            "key_id": settings.RAZORPAY_KEY_ID,
        }
        return Response(
            {
                "order": serializer.data,
                "payment": payment_payload,
                "reservation_expires_at": order.reservation_expires_at,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    def _ensure_checkout_payment(self, order, idempotency_key):
        existing_payment = Payment.objects.filter(idempotency_key=idempotency_key).first()
        if existing_payment:
            if existing_payment.order_id != order.id:
                raise IntegrityError("Idempotency key is already used.")
            return existing_payment, False

        amount_paise = int((Decimal(order.total_amount) * Decimal("100")).quantize(Decimal("1")))
        razorpay_order = create_razorpay_order(
            amount=amount_paise,
            currency="INR",
            receipt=f"order_{order.id}",
        )

        payment = Payment.objects.create(
            order=order,
            idempotency_key=idempotency_key,
            razorpay_order_id=razorpay_order["id"],
            amount=razorpay_order.get("amount", amount_paise),
            currency=razorpay_order.get("currency", "INR"),
            status=razorpay_order.get("status", Payment.Status.CREATED),
            raw_response=razorpay_order,
        )
        return payment, True

    def get_throttles(self):
        if self.action in {"create", "create_order", "checkout_from_cart"}:
            return [OrderCreateRateThrottle()]
        return super().get_throttles()

    def get_queryset(self):
        return (
            Order.objects.filter(user=self.request.user)
            .select_related("shipping_address", "applied_coupon")
            .prefetch_related("items__product", "shipping_events", "events")
        )

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action in ['retrieve', 'list']:
            return OrderDetailSerializer
        return self.serializer_class

    def perform_create(self, serializer):
        idempotency_key = self.request.headers.get("Idempotency-Key")
        if idempotency_key:
            existing_order = (
                Order.objects.filter(user=self.request.user, idempotency_key=idempotency_key)
                .select_related("shipping_address", "applied_coupon")
                .prefetch_related("items__product")
                .first()
            )
            if existing_order:
                serializer.instance = existing_order
                return
            try:
                serializer.save(user=self.request.user, idempotency_key=idempotency_key)
            except IntegrityError:
                existing_order = Order.objects.filter(user=self.request.user, idempotency_key=idempotency_key).first()
                if existing_order:
                    serializer.instance = existing_order
                    return
                raise
            return
        serializer.save(user=self.request.user)

    @decorators.action(detail=False, methods=["post"], url_path="create")
    @transaction.atomic
    def create_order(self, request):
        """
        Create an order with items.
        
        Request body:
        {
            "items": [
                {"product_id": 1, "quantity": 2},
                {"product_id": 2, "quantity": 1}
            ]
        }
        """
        serializer = CreateOrderSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        
        # Return the created order with items
        output_serializer = OrderDetailSerializer(order, context={"request": request})
        return Response(output_serializer.data, status=201)

    @decorators.action(detail=False, methods=["post"], url_path="checkout-from-cart")
    def checkout_from_cart(self, request):
        metric_incr("checkout.started")
        idempotency_key = request.META.get("HTTP_IDEMPOTENCY_KEY") or request.data.get("idempotency_key")
        if not idempotency_key:
            return Response(
                {"detail": "Idempotency-Key header or idempotency_key field is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
            logger.error(
                "Razorpay key configuration is missing: key_id=%s key_secret=%s",
                bool(settings.RAZORPAY_KEY_ID),
                bool(settings.RAZORPAY_KEY_SECRET),
            )
            return Response({"detail": "Payment gateway configuration error."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        try:
            with transaction.atomic():
                cart = Cart.objects.select_for_update().filter(user=request.user, is_active=True).first()
                if not cart:
                    return Response({"detail": "Active cart not found."}, status=status.HTTP_404_NOT_FOUND)

                cart_items = list(
                    CartItem.objects.select_for_update()
                    .select_related("product", "product__category")
                    .filter(cart=cart)
                )
                if not cart_items:
                    return Response({"detail": "Cart is empty."}, status=status.HTTP_400_BAD_REQUEST)

                existing_cart_order = (
                    Order.objects.select_related("applied_coupon", "source_cart")
                    .prefetch_related("items__product")
                    .filter(user=request.user, source_cart=cart)
                    .order_by("-created_at")
                    .first()
                )
                if existing_cart_order:
                    if existing_cart_order.payment_status in {
                        Order.PaymentStatus.PAID,
                        Order.PaymentStatus.REFUNDED,
                        Order.PaymentStatus.CANCELLED,
                    }:
                        return Response(
                            {
                                "detail": "Checkout already completed for this cart.",
                                "order_id": existing_cart_order.id,
                                "payment_status": existing_cart_order.payment_status,
                            },
                            status=status.HTTP_409_CONFLICT,
                        )
                    if (
                        existing_cart_order.idempotency_key
                        and existing_cart_order.idempotency_key != idempotency_key
                    ):
                        return Response(
                            {
                                "detail": "Checkout already initiated for this cart.",
                                "order_id": existing_cart_order.id,
                            },
                            status=status.HTTP_409_CONFLICT,
                        )
                    if (
                        existing_cart_order.reservation_expires_at
                        and existing_cart_order.reservation_expires_at < timezone.now()
                    ):
                        release_order_inventory(existing_cart_order, reason="reservation_expired")
                        return Response(
                            {"detail": "Reservation expired. Please retry checkout."},
                            status=status.HTTP_409_CONFLICT,
                        )
                    payment, _ = self._ensure_checkout_payment(existing_cart_order, idempotency_key)
                    return self._build_checkout_response(existing_cart_order, payment, request, created=False)

                existing_idempotent_order = (
                    Order.objects.select_related("applied_coupon", "source_cart")
                    .prefetch_related("items__product")
                    .filter(user=request.user, idempotency_key=idempotency_key)
                    .first()
                )
                if existing_idempotent_order:
                    if existing_idempotent_order.payment_status in {
                        Order.PaymentStatus.PAID,
                        Order.PaymentStatus.REFUNDED,
                        Order.PaymentStatus.CANCELLED,
                    }:
                        return Response(
                            {
                                "detail": "Checkout already completed for this order.",
                                "order_id": existing_idempotent_order.id,
                                "payment_status": existing_idempotent_order.payment_status,
                            },
                            status=status.HTTP_409_CONFLICT,
                        )
                    if (
                        existing_idempotent_order.source_cart_id
                        and existing_idempotent_order.source_cart_id != cart.id
                    ):
                        return Response(
                            {"detail": "Idempotency key already used for another checkout."},
                            status=status.HTTP_409_CONFLICT,
                        )
                    if (
                        existing_idempotent_order.reservation_expires_at
                        and existing_idempotent_order.reservation_expires_at < timezone.now()
                    ):
                        release_order_inventory(existing_idempotent_order, reason="reservation_expired")
                        return Response(
                            {"detail": "Reservation expired. Please retry checkout."},
                            status=status.HTTP_409_CONFLICT,
                        )
                    payment, _ = self._ensure_checkout_payment(existing_idempotent_order, idempotency_key)
                    return self._build_checkout_response(existing_idempotent_order, payment, request, created=False)

                product_ids = [item.product_id for item in cart_items]
                products = {
                    product.id: product
                    for product in Product.objects.select_for_update().filter(id__in=product_ids)
                }

                errors = []
                total_amount = Decimal("0.00")
                order_items = []
                for item in cart_items:
                    product = products.get(item.product_id)
                    if not product or not product.is_active:
                        errors.append({"product_id": item.product_id, "reason": "unavailable"})
                        continue
                    if product.stock_quantity < item.quantity:
                        errors.append(
                            {
                                "product_id": item.product_id,
                                "reason": "insufficient_stock",
                                "available": product.stock_quantity,
                                "requested": item.quantity,
                            }
                        )
                        continue

                    total_amount += product.price * item.quantity
                    order_items.append(
                        OrderItem(
                            order=None,
                            product=product,
                            quantity=item.quantity,
                            price=product.price,
                        )
                    )

                if errors:
                    raise serializers.ValidationError(
                        {"detail": "Cart contains unavailable items.", "items": errors}
                    )

                total_amount = total_amount.quantize(Decimal("0.01"))
                order = Order.objects.create(
                    user=request.user,
                    total_amount=total_amount,
                    status=Order.Status.PENDING_PAYMENT,
                    payment_status=Order.PaymentStatus.PENDING_PAYMENT,
                    idempotency_key=idempotency_key,
                    source_cart=cart,
                )
                bind_context(order_id=order.id, user_id=request.user.id)

                for order_item in order_items:
                    order_item.order = order
                OrderItem.objects.bulk_create(order_items)
                reserve_order_inventory(order)
                create_vendor_orders_for_order(order)

                payment, _ = self._ensure_checkout_payment(order, idempotency_key)
                bind_context(payment_id=payment.id)
                log_event("checkout_session_created", order_id=order.id, payment_id=payment.id)
                return self._build_checkout_response(order, payment, request, created=True)
        except (RazorpayIntegrationError, KeyError, InvalidOperation):
            metric_incr("checkout.failed")
            logger.exception("Checkout failed while creating payment order")
            log_event("checkout_failed_payment_init", level="error")
            return Response({"detail": "Unable to initialize payment."}, status=status.HTTP_502_BAD_GATEWAY)
        except serializers.ValidationError:
            metric_incr("reservation.failed")
            metric_incr("checkout.failed")
            log_event("inventory_reservation_failed", level="warning")
            raise
        except IntegrityError:
            metric_incr("checkout.failed")
            existing_order = (
                Order.objects.select_related("applied_coupon", "source_cart")
                .prefetch_related("items__product")
                .filter(user=request.user, idempotency_key=idempotency_key)
                .first()
            )
            if existing_order:
                if existing_order.payment_status in {
                    Order.PaymentStatus.PAID,
                    Order.PaymentStatus.REFUNDED,
                    Order.PaymentStatus.CANCELLED,
                }:
                    return Response(
                        {
                            "detail": "Checkout already completed for this order.",
                            "order_id": existing_order.id,
                            "payment_status": existing_order.payment_status,
                        },
                        status=status.HTTP_409_CONFLICT,
                    )
                payment, _ = self._ensure_checkout_payment(existing_order, idempotency_key)
                return self._build_checkout_response(existing_order, payment, request, created=False)
            return Response({"detail": "Duplicate checkout attempt detected."}, status=status.HTTP_409_CONFLICT)

    @decorators.action(detail=False, methods=["get"], url_path="my-orders")
    def my_orders(self, request):
        """
        Get all orders for the authenticated user.
        This is an alias for the list action with a more descriptive endpoint name.
        """
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = OrderDetailSerializer(page, many=True, context={"request": request})
            return self.get_paginated_response(serializer.data)

        serializer = OrderDetailSerializer(queryset, many=True, context={"request": request})
        return Response(serializer.data)

    @decorators.action(detail=True, methods=["post"], url_path="apply-coupon")
    @transaction.atomic
    def apply_coupon(self, request, pk=None):
        order = (
            Order.objects.select_for_update()
            .select_related("applied_coupon")
            .filter(id=pk, user=request.user)
            .first()
        )
        if not order:
            return Response({"detail": "Order not found."}, status=404)
        if order.payment_status not in {Order.PaymentStatus.PENDING, Order.PaymentStatus.PENDING_PAYMENT}:
            return Response({"detail": "Coupon can only be applied to pending payment orders."}, status=400)
        requested_code = str(request.data.get("code", "")).upper()
        if order.applied_coupon_id:
            if order.applied_coupon and order.applied_coupon.code == requested_code:
                return Response(
                    {
                        "order_id": order.id,
                        "coupon_code": order.applied_coupon.code,
                        "gross_amount": order.gross_amount or order.total_amount,
                        "discount_amount": order.coupon_discount,
                        "net_amount": order.total_amount,
                    },
                    status=200,
                )
            return Response({"detail": "A different coupon is already applied to this order."}, status=400)

        serializer = ApplyCouponSerializer(data=request.data, context={"request": request, "order": order})
        serializer.is_valid(raise_exception=True)
        coupon = serializer.validated_data["coupon"]

        gross_amount = (order.gross_amount or order.total_amount).quantize(Decimal("0.01"))
        discount_amount = serializer.calculate_discount(gross_amount)
        net_amount = (gross_amount - discount_amount).quantize(Decimal("0.01"))

        order.gross_amount = gross_amount
        order.coupon_discount = discount_amount
        order.total_amount = net_amount
        order.applied_coupon = coupon
        order.save(update_fields=["gross_amount", "coupon_discount", "total_amount", "applied_coupon", "updated_at"])

        CouponUsage.objects.create(
            coupon=coupon,
            user=request.user,
            order=order,
            discount_amount=discount_amount,
        )
        Coupon.objects.filter(id=coupon.id).update(used_count=F("used_count") + 1)

        return Response(
            {
                "order_id": order.id,
                "coupon_code": coupon.code,
                "gross_amount": gross_amount,
                "discount_amount": discount_amount,
                "net_amount": net_amount,
            },
            status=200,
        )

    @decorators.action(detail=True, methods=["post"], url_path="cancel")
    @transaction.atomic
    def cancel_order(self, request, pk=None):
        order = (
            Order.objects.select_for_update()
            .filter(id=pk, user=request.user)
            .first()
        )
        if not order:
            return Response({"detail": "Order not found."}, status=404)
        if order.status in {Order.Status.SHIPPED, Order.Status.DELIVERED, Order.Status.CANCELLED, Order.Status.REFUNDED}:
            return Response({"detail": "This order can no longer be cancelled."}, status=400)
        previous_status = order.status
        previous_payment_status = order.payment_status
        order.status = Order.Status.CANCELLED
        order.save(update_fields=["status", "updated_at"])
        order.events.create(
            previous_status=previous_status,
            new_status=Order.Status.CANCELLED,
            previous_payment_status=previous_payment_status,
            new_payment_status=order.payment_status,
            changed_by=request.user,
            note="Cancelled by customer",
        )
        send_order_email_task.delay("order_cancelled", order.id)
        return Response({"detail": "Order cancelled successfully."}, status=200)


class OrderItemViewSet(viewsets.ModelViewSet):
    serializer_class = OrderItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return OrderItem.objects.filter(order__user=self.request.user).select_related("order", "product")


class ShippingAddressViewSet(viewsets.ModelViewSet):
    serializer_class = ShippingAddressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ShippingAddress.objects.filter(order__user=self.request.user).select_related("order")


class CouponViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CouponSerializer
    permission_classes = [permissions.IsAdminUser]
    queryset = Coupon.objects.all()


class AdminAnalyticsView(APIView):
    permission_classes = [permissions.IsAdminUser]
    throttle_classes = [AdminRateThrottle]

    def get(self, request):
        if request.method == "GET":
            try:
                cached = cache.get("admin_analytics_summary")
                if cached is not None:
                    return Response(cached)
            except Exception:
                pass

        total_orders = Order.objects.count()
        total_revenue = (
            Order.objects.filter(payment_status=Order.PaymentStatus.PAID).aggregate(
                total=Coalesce(Sum("total_amount"), Decimal("0.00"))
            )["total"]
        )
        total_users = get_user_model().objects.count()
        top_products = list(
            OrderItem.objects.filter(order__payment_status=Order.PaymentStatus.PAID)
            .values("product_id", "product__name")
            .annotate(total_sold=Coalesce(Sum("quantity"), 0))
            .order_by("-total_sold", "product_id")[:5]
        )
        recent_orders = [
            {
                "order_id": order.id,
                "user_email": order.user.email,
                "total_amount": str(order.total_amount),
                "status": order.status,
                "created_at": order.created_at.isoformat(),
            }
            for order in Order.objects.select_related("user").order_by("-created_at")[:10]
        ]

        response_data = {
            "total_orders": total_orders,
            "total_revenue": f"{total_revenue:.2f}",
            "total_users": total_users,
            "top_products": [
                {
                    "product_id": row["product_id"],
                    "name": row["product__name"],
                    "total_sold": row["total_sold"],
                }
                for row in top_products
            ],
            "recent_orders": recent_orders,
        }
        if request.method == "GET":
            try:
                cache.set("admin_analytics_summary", response_data, timeout=120)
            except Exception:
                pass
        return Response(response_data)
