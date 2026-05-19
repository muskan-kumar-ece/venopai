from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

from django.db import transaction
from django.db.models import Count, DecimalField, F, IntegerField, Max, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from core.throttles import AdminRateThrottle
from orders.models import InventoryReservation, Order, OrderEvent, ShippingEvent
from orders.tasks import send_order_email_task
from payments.models import Payment
from products.models import Product
from users.models import Referral

from .serializers import (
    AdminDeliverOrderSerializer,
    AdminFailedPaymentSerializer,
    AdminInventoryItemSerializer,
    AdminOrderDetailSerializer,
    AdminOrderListSerializer,
    AdminShipOrderSerializer,
    AdminOrderStatusUpdateSerializer,
    AdminReservationSerializer,
    AnalyticsSummarySerializer,
)

TRACKING_ID_PREFIX = "TRK"


class AdminOrderPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200


class AdminInventoryPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = "page_size"
    max_page_size = 500


class AdminReservationPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = "page_size"
    max_page_size = 500


class AdminFailedPaymentPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200


class AnalyticsSummaryView(APIView):
    permission_classes = [IsAdminUser]
    throttle_classes = [AdminRateThrottle]

    def get(self, request):
        today = timezone.localdate()
        last_7_days_start = today - timedelta(days=6)

        metrics = Order.objects.aggregate(
            gross_revenue=Coalesce(
                Sum(
                    Coalesce(F("gross_amount"), F("total_amount")),
                    filter=Q(payment_status=Order.PaymentStatus.PAID),
                ),
                Value(Decimal("0.00")),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            ),
            discount_amount=Coalesce(
                Sum("coupon_discount", filter=Q(payment_status=Order.PaymentStatus.PAID)),
                Value(Decimal("0.00")),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            ),
            net_revenue=Coalesce(
                Sum("total_amount", filter=Q(payment_status=Order.PaymentStatus.PAID)),
                Value(Decimal("0.00")),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            ),
            total_orders=Count("id"),
            total_paid_orders=Count("id", filter=Q(payment_status=Order.PaymentStatus.PAID)),
            total_refunded_orders=Count("id", filter=Q(payment_status=Order.PaymentStatus.REFUNDED)),
            revenue_from_referrals=Coalesce(
                Sum(
                    "total_amount",
                    filter=Q(payment_status=Order.PaymentStatus.PAID, user__referral_record__isnull=False),
                ),
                Value(Decimal("0.00")),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            ),
            today_revenue=Coalesce(
                Sum(
                    "total_amount",
                    filter=Q(
                        payment_status=Order.PaymentStatus.PAID,
                        created_at__date=today,
                    ),
                ),
                Value(Decimal("0.00")),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            ),
            today_orders=Count("id", filter=Q(created_at__date=today)),
            last_7_days_revenue=Coalesce(
                Sum(
                    "total_amount",
                    filter=Q(
                        payment_status=Order.PaymentStatus.PAID,
                        created_at__date__gte=last_7_days_start,
                    ),
                ),
                Value(Decimal("0.00")),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            ),
        )

        total_orders = metrics["total_orders"]
        if total_orders:
            refund_rate_percent = float(
                (Decimal(metrics["total_refunded_orders"]) / Decimal(total_orders)) * Decimal("100")
            )
        else:
            refund_rate_percent = 0.0

        referral_metrics = Referral.objects.aggregate(
            total_referrals=Count("id"),
            successful_referrals=Count("id", filter=Q(reward_issued=True)),
        )

        serializer = AnalyticsSummarySerializer(
            {
                **metrics,
                **referral_metrics,
                "total_revenue": metrics["net_revenue"],
                "refund_rate_percent": round(refund_rate_percent, 2),
            }
        )
        return Response(serializer.data)


class AdminOperationsSummaryView(APIView):
    permission_classes = [IsAdminUser]
    throttle_classes = [AdminRateThrottle]

    def get(self, request):
        now = timezone.now()
        pending_statuses = [
            Order.PaymentStatus.PENDING,
            Order.PaymentStatus.PENDING_PAYMENT,
            Order.PaymentStatus.PAYMENT_PROCESSING,
        ]
        summary = {
            "active_reservations": InventoryReservation.objects.filter(
                status=InventoryReservation.Status.ACTIVE
            ).count(),
            "reservations_expiring_soon": InventoryReservation.objects.filter(
                status=InventoryReservation.Status.ACTIVE,
                expires_at__lte=now + timedelta(minutes=5),
            ).count(),
            "pending_payment_orders": Order.objects.filter(payment_status__in=pending_statuses).count(),
            "failed_payments": Payment.objects.filter(status=Payment.Status.FAILED).count(),
            "stale_pending_orders": Order.objects.filter(
                payment_status__in=[Order.PaymentStatus.PENDING, Order.PaymentStatus.PENDING_PAYMENT],
                reservation_expires_at__lt=now,
            ).count(),
        }
        return Response(summary)


class AdminInventoryOverviewView(APIView):
    permission_classes = [IsAdminUser]
    throttle_classes = [AdminRateThrottle]

    def get(self, request):
        low_stock_only = str(request.query_params.get("low_stock_only", "")).lower() in {"1", "true", "yes"}
        try:
            low_stock_threshold = int(request.query_params.get("low_stock_threshold", 5))
        except (TypeError, ValueError):
            low_stock_threshold = 5

        queryset = (
            Product.objects.annotate(
                active_reserved=Coalesce(
                    Sum(
                        "inventory_reservations__quantity",
                        filter=Q(inventory_reservations__status=InventoryReservation.Status.ACTIVE),
                    ),
                    Value(0),
                    output_field=IntegerField(),
                ),
                last_reservation_expires_at=Max(
                    "inventory_reservations__expires_at",
                    filter=Q(inventory_reservations__status=InventoryReservation.Status.ACTIVE),
                ),
            )
            .annotate(available_quantity=F("stock_quantity") - F("active_reserved"))
            .order_by("available_quantity", "id")
        )

        if low_stock_only:
            queryset = queryset.filter(available_quantity__lte=low_stock_threshold)

        paginator = AdminInventoryPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = AdminInventoryItemSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class AdminReservationListView(APIView):
    permission_classes = [IsAdminUser]
    throttle_classes = [AdminRateThrottle]

    def get(self, request):
        queryset = InventoryReservation.objects.select_related("order", "product").order_by("expires_at")
        status_filter = request.query_params.get("status")
        if status_filter:
            valid_statuses = {choice[0] for choice in InventoryReservation.Status.choices}
            if status_filter in valid_statuses:
                queryset = queryset.filter(status=status_filter)

        order_id = request.query_params.get("order_id")
        if order_id and str(order_id).isdigit():
            queryset = queryset.filter(order_id=int(order_id))

        product_id = request.query_params.get("product_id")
        if product_id and str(product_id).isdigit():
            queryset = queryset.filter(product_id=int(product_id))

        paginator = AdminReservationPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = AdminReservationSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class AdminFailedPaymentsView(APIView):
    permission_classes = [IsAdminUser]
    throttle_classes = [AdminRateThrottle]

    def get(self, request):
        try:
            since_hours = int(request.query_params.get("since_hours", 24))
        except (TypeError, ValueError):
            since_hours = 24
        since_time = timezone.now() - timedelta(hours=since_hours)
        queryset = (
            Payment.objects.select_related("order", "order__user")
            .filter(status=Payment.Status.FAILED, updated_at__gte=since_time)
            .order_by("-updated_at")
        )

        order_id = request.query_params.get("order_id")
        if order_id and str(order_id).isdigit():
            queryset = queryset.filter(order_id=int(order_id))

        paginator = AdminFailedPaymentPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = AdminFailedPaymentSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class AdminOrderListView(APIView):
    permission_classes = [IsAdminUser]
    throttle_classes = [AdminRateThrottle]

    def get(self, request):
        queryset = Order.objects.select_related("user").order_by("-created_at")
        status_filter = request.query_params.get("status")
        date_filter = request.query_params.get("date")
        search = request.query_params.get("search")

        if status_filter:
            normalized_status = Order.Status.CONFIRMED if status_filter == "processing" else status_filter
            valid_statuses = {choice[0] for choice in Order.Status.choices}
            if normalized_status in valid_statuses:
                queryset = queryset.filter(status=normalized_status)

        if date_filter:
            queryset = queryset.filter(created_at__date=date_filter)

        if search:
            normalized_search = search.strip()
            search_query = Q(user__email__icontains=normalized_search)
            if normalized_search.isdigit():
                search_query = search_query | Q(id=int(normalized_search))
            queryset = queryset.filter(search_query)

        paginator = AdminOrderPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = AdminOrderListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class AdminOrderDetailView(APIView):
    permission_classes = [IsAdminUser]
    throttle_classes = [AdminRateThrottle]

    def get(self, request, order_id):
        order = get_object_or_404(
            Order.objects.select_related("user", "shipping_address").prefetch_related(
                "items__product",
                "events__changed_by",
                "shipping_events",
            ),
            pk=order_id,
        )
        serializer = AdminOrderDetailSerializer(order)
        return Response(serializer.data)


class AdminOrderStatusUpdateView(APIView):
    permission_classes = [IsAdminUser]
    throttle_classes = [AdminRateThrottle]

    @transaction.atomic
    def post(self, request, order_id):
        order = get_object_or_404(Order.objects.select_for_update(), pk=order_id)
        serializer = AdminOrderStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        previous_status = order.status
        previous_payment_status = order.payment_status
        new_status = serializer.validated_data["status"]
        new_payment_status = serializer.validated_data.get("payment_status", order.payment_status)
        note = serializer.validated_data.get("note", "")

        if previous_status != new_status or previous_payment_status != new_payment_status:
            order.status = new_status
            order.payment_status = new_payment_status
            order.save(update_fields=["status", "payment_status", "updated_at"])
            OrderEvent.objects.create(
                order=order,
                previous_status=previous_status,
                new_status=new_status,
                previous_payment_status=previous_payment_status,
                new_payment_status=new_payment_status,
                changed_by=request.user,
                note=note,
            )
            if new_status == Order.Status.SHIPPED:
                send_order_email_task.delay("order_shipped", order.id)
            elif new_status == Order.Status.DELIVERED:
                send_order_email_task.delay("order_delivered", order.id)
            elif new_status == Order.Status.CANCELLED:
                send_order_email_task.delay("order_cancelled", order.id)

        order = (
            Order.objects.select_related("user", "shipping_address")
            .prefetch_related("items__product", "events__changed_by", "shipping_events")
            .get(pk=order.pk)
        )
        return Response(AdminOrderDetailSerializer(order).data)


class AdminShipOrderView(APIView):
    permission_classes = [IsAdminUser]
    throttle_classes = [AdminRateThrottle]

    @transaction.atomic
    def post(self, request, order_id):
        order = get_object_or_404(Order.objects.select_for_update(), pk=order_id)
        serializer = AdminShipOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if order.status == Order.Status.DELIVERED:
            return Response({"detail": "Cannot ship a delivered order."}, status=400)
        if order.status != Order.Status.SHIPPED:
            order.status = Order.Status.SHIPPED
        if not order.tracking_id:
            order.tracking_id = f"{TRACKING_ID_PREFIX}-{uuid4().hex[:12].upper()}"
        shipping_provider = serializer.validated_data.get("shipping_provider")
        if shipping_provider:
            order.shipping_provider = shipping_provider
        elif not order.shipping_provider:
            order.shipping_provider = "Manual"
        if not order.shipped_at:
            order.shipped_at = timezone.now()
        order.save(update_fields=["status", "tracking_id", "shipping_provider", "shipped_at", "updated_at"])
        ShippingEvent.objects.create(
            order=order,
            event_type=ShippingEvent.EventType.CREATED,
            location=serializer.validated_data.get("location", ""),
        )
        send_order_email_task.delay("order_shipped", order.id)
        order = (
            Order.objects.select_related("user", "shipping_address")
            .prefetch_related("items__product", "events__changed_by", "shipping_events")
            .get(pk=order.pk)
        )
        return Response(AdminOrderDetailSerializer(order).data)


class AdminDeliverOrderView(APIView):
    permission_classes = [IsAdminUser]
    throttle_classes = [AdminRateThrottle]

    @transaction.atomic
    def post(self, request, order_id):
        order = get_object_or_404(Order.objects.select_for_update(), pk=order_id)
        serializer = AdminDeliverOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if order.status == Order.Status.DELIVERED:
            return Response({"detail": "Order already delivered."}, status=200)
        if order.status != Order.Status.SHIPPED:
            return Response({"detail": "Only shipped orders can be marked delivered."}, status=400)
        order.status = Order.Status.DELIVERED
        order.delivered_at = timezone.now()
        order.save(update_fields=["status", "delivered_at", "updated_at"])
        ShippingEvent.objects.create(
            order=order,
            event_type=ShippingEvent.EventType.DELIVERED,
            location=serializer.validated_data.get("location", ""),
        )
        send_order_email_task.delay("order_delivered", order.id)
        order = (
            Order.objects.select_related("user", "shipping_address")
            .prefetch_related("items__product", "events__changed_by", "shipping_events")
            .get(pk=order.pk)
        )
        return Response(AdminOrderDetailSerializer(order).data)
