from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from products.models import Product
from products.media import build_cloudinary_url
from vendors.services import create_vendor_orders_for_order
from .models import Cart, CartItem, Coupon, CouponUsage, Order, OrderItem, ShippingAddress, ShippingEvent


class CartSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cart
        fields = ("id", "user", "is_active", "created_at", "updated_at")
        read_only_fields = ("id", "user", "created_at", "updated_at")


class CartProductSummarySerializer(serializers.ModelSerializer):
    """Lightweight nested product payload for cart line items."""

    category_name = serializers.CharField(source="category.name", read_only=True)
    image_url = serializers.SerializerMethodField()
    image_url_card = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = (
            "id",
            "name",
            "slug",
            "sku",
            "price",
            "stock_quantity",
            "is_active",
            "is_refurbished",
            "condition_grade",
            "category_name",
            "image_url",
            "image_url_card",
        )
        read_only_fields = fields

    def get_image_url(self, product):
        images = list(product.images.all())
        if not images:
            return None
        primary = next((image for image in images if image.is_primary), images[0])
        return primary.image_url

    def get_image_url_card(self, product):
        images = list(product.images.all())
        if not images:
            return None
        primary = next((image for image in images if image.is_primary), images[0])
        return build_cloudinary_url(primary.cloudinary_public_id, "card") or primary.image_url


class CartItemReadSerializer(serializers.ModelSerializer):
    product = CartProductSummarySerializer(read_only=True)
    line_total = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = (
            "id",
            "cart",
            "product",
            "quantity",
            "line_total",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_line_total(self, obj):
        total = (obj.product.price * obj.quantity).quantize(Decimal("0.01"))
        return str(total)


class CartItemWriteSerializer(serializers.ModelSerializer):
    """Create/update cart lines by product id; merges quantity on duplicate product."""

    def validate_cart(self, cart):
        request = self.context.get("request")
        if request and request.user.is_authenticated and cart.user_id != request.user.id:
            raise serializers.ValidationError("You can only add items to your own cart.")
        if not cart.is_active:
            raise serializers.ValidationError("You can only modify your active cart.")
        return cart

    def validate_product(self, product):
        if not product.is_active:
            raise serializers.ValidationError("Product is not available.")
        return product

    class Meta:
        model = CartItem
        fields = ("id", "cart", "product", "quantity", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")
        # Uniqueness is enforced in create() by merging quantity (one row per product).
        validators = []

    @transaction.atomic
    def create(self, validated_data):
        cart = validated_data["cart"]
        product = validated_data["product"]
        quantity = validated_data.get("quantity", 1)

        existing_item = (
            CartItem.objects.select_for_update()
            .filter(cart=cart, product=product)
            .first()
        )
        if existing_item is not None:
            existing_item.quantity += quantity
            existing_item.save(update_fields=["quantity", "updated_at"])
            return existing_item

        return CartItem.objects.create(cart=cart, product=product, quantity=quantity)


# Backward-compatible alias for imports expecting CartItemSerializer on write paths.
CartItemSerializer = CartItemWriteSerializer


class ServerCartViewSerializer(serializers.ModelSerializer):
    """Active cart with nested items and rollups for the storefront API layer."""

    items = CartItemReadSerializer(many=True, read_only=True)
    item_count = serializers.SerializerMethodField()
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = (
            "id",
            "user",
            "is_active",
            "created_at",
            "updated_at",
            "items",
            "item_count",
            "subtotal",
        )
        read_only_fields = fields

    def get_item_count(self, cart):
        return sum(item.quantity for item in cart.items.all())

    def get_subtotal(self, cart):
        total = Decimal("0.00")
        for item in cart.items.all():
            total += item.product.price * item.quantity
        return str(total.quantize(Decimal("0.01")))


class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = (
            "id",
            "user",
            "total_amount",
            "gross_amount",
            "coupon_discount",
            "applied_coupon",
            "status",
            "payment_status",
            "tracking_id",
            "reservation_expires_at",
            "reservation_released_at",
            "shipping_provider",
            "shipped_at",
            "delivered_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "user",
            "status",
            "payment_status",
            "gross_amount",
            "coupon_discount",
            "applied_coupon",
            "created_at",
            "updated_at",
        )


class OrderItemSerializer(serializers.ModelSerializer):
    def validate_order(self, order):
        request = self.context.get("request")
        if request and request.user.is_authenticated and order.user_id != request.user.id:
            raise serializers.ValidationError("You can only add items to your own order.")
        return order

    class Meta:
        model = OrderItem
        fields = ("id", "order", "product", "quantity", "price", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")


class OrderItemInputSerializer(serializers.Serializer):
    """Serializer for order item input when creating an order."""
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)

    def validate_product_id(self, value):
        """Validate that the product exists and is active."""
        try:
            product = Product.objects.get(id=value, is_active=True)
        except Product.DoesNotExist:
            raise serializers.ValidationError(f"Product with id {value} does not exist or is inactive.")
        return value


class CreateOrderSerializer(serializers.Serializer):
    """Serializer for creating an order with items."""
    items = OrderItemInputSerializer(many=True)

    def validate_items(self, value):
        """Validate that at least one item is provided."""
        if not value:
            raise serializers.ValidationError("At least one item is required to create an order.")
        return value

    @transaction.atomic
    def create(self, validated_data):
        """Create an order with items."""
        request = self.context.get("request")
        items_data = validated_data.get("items", [])

        # Fetch all products in one query
        product_ids = [item["product_id"] for item in items_data]
        products = {p.id: p for p in Product.objects.filter(id__in=product_ids, is_active=True)}

        # Calculate total price
        total_price = Decimal("0.00")
        order_items_data = []
        for item_data in items_data:
            product = products.get(item_data["product_id"])
            if not product:
                raise serializers.ValidationError(
                    f"Product with id {item_data['product_id']} does not exist or is inactive."
                )
            item_total = product.price * item_data["quantity"]
            total_price += item_total
            order_items_data.append({
                "product": product,
                "quantity": item_data["quantity"],
                "price": product.price,
            })

        # Create the order
        order = Order.objects.create(
            user=request.user,
            total_amount=total_price,
            status=Order.Status.PENDING,
            payment_status=Order.PaymentStatus.PENDING,
        )

        # Create order items
        order_items = [
            OrderItem(
                order=order,
                product=item["product"],
                quantity=item["quantity"],
                price=item["price"],
            )
            for item in order_items_data
        ]
        OrderItem.objects.bulk_create(order_items)
        create_vendor_orders_for_order(order)

        return order


class OrderDetailSerializer(serializers.ModelSerializer):
    """Serializer for order detail with items."""
    items = OrderItemSerializer(many=True, read_only=True)
    shipping_events = serializers.SerializerMethodField()

    def get_shipping_events(self, obj):
        events = obj.shipping_events.all()
        return ShippingEventSerializer(events, many=True).data

    class Meta:
        model = Order
        fields = (
            "id",
            "user",
            "total_amount",
            "gross_amount",
            "coupon_discount",
            "applied_coupon",
            "status",
            "payment_status",
            "tracking_id",
            "reservation_expires_at",
            "reservation_released_at",
            "shipping_provider",
            "shipped_at",
            "delivered_at",
            "shipping_events",
            "items",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "user",
            "status",
            "payment_status",
            "gross_amount",
            "coupon_discount",
            "applied_coupon",
            "created_at",
            "updated_at",
        )


class ShippingAddressSerializer(serializers.ModelSerializer):
    def validate_order(self, order):
        request = self.context.get("request")
        if request and request.user.is_authenticated and order.user_id != request.user.id:
            raise serializers.ValidationError("You can only add a shipping address to your own order.")
        return order

    class Meta:
        model = ShippingAddress
        fields = (
            "id",
            "order",
            "full_name",
            "phone_number",
            "address_line_1",
            "address_line_2",
            "city",
            "state",
            "postal_code",
            "country",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class ShippingEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShippingEvent
        fields = (
            "id",
            "event_type",
            "location",
            "timestamp",
        )


class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = (
            "id",
            "code",
            "discount_type",
            "discount_value",
            "minimum_order_amount",
            "max_uses",
            "used_count",
            "per_user_limit",
            "eligible_user",
            "valid_from",
            "valid_until",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "used_count", "created_at", "updated_at")


class ApplyCouponSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=50)

    def validate_code(self, value):
        return value.upper()

    def validate(self, attrs):
        request = self.context["request"]
        order = self.context["order"]
        now = timezone.now()
        coupon = (
            Coupon.objects.select_for_update()
            .filter(code=attrs["code"])
            .first()
        )
        if not coupon:
            raise serializers.ValidationError({"code": "Invalid coupon code."})
        if not coupon.is_active:
            raise serializers.ValidationError({"code": "Coupon is inactive."})
        if coupon.valid_from > now or coupon.valid_until < now:
            raise serializers.ValidationError({"code": "Coupon is not valid at this time."})
        order_base_amount = order.gross_amount or order.total_amount
        if coupon.minimum_order_amount and order_base_amount < coupon.minimum_order_amount:
            raise serializers.ValidationError({"code": "Order does not meet minimum amount for this coupon."})
        if coupon.max_uses is not None and coupon.used_count >= coupon.max_uses:
            raise serializers.ValidationError({"code": "Coupon usage limit exceeded."})
        if coupon.per_user_limit is not None:
            user_usage_count = CouponUsage.objects.filter(coupon=coupon, user=request.user).count()
            if user_usage_count >= coupon.per_user_limit:
                raise serializers.ValidationError({"code": "Per-user coupon usage limit exceeded."})
        if coupon.eligible_user_id and coupon.eligible_user_id != request.user.id:
            raise serializers.ValidationError({"code": "Coupon is not eligible for this user."})
        attrs["coupon"] = coupon
        return attrs

    def calculate_discount(self, order_amount: Decimal) -> Decimal:
        coupon: Coupon = self.validated_data["coupon"]
        if coupon.discount_type == Coupon.DiscountType.PERCENTAGE:
            discount = (order_amount * coupon.discount_value / Decimal("100")).quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP,
            )
        else:
            discount = coupon.discount_value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        max_discount = max(order_amount - Decimal("0.01"), Decimal("0.00"))
        return min(discount, max_discount)
