from rest_framework import serializers

from orders.models import InventoryReservation, Order, OrderEvent, OrderItem, ShippingAddress, ShippingEvent
from payments.models import Payment
from products.models import Product

class AnalyticsSummarySerializer(serializers.Serializer):
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    gross_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    discount_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    net_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_orders = serializers.IntegerField()
    total_paid_orders = serializers.IntegerField()
    total_refunded_orders = serializers.IntegerField()
    total_referrals = serializers.IntegerField()
    successful_referrals = serializers.IntegerField()
    revenue_from_referrals = serializers.DecimalField(max_digits=12, decimal_places=2)
    refund_rate_percent = serializers.FloatField()
    today_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    today_orders = serializers.IntegerField()
    last_7_days_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)


class AdminOrderListSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = Order
        fields = (
            "id",
            "user_email",
            "total_amount",
            "payment_status",
            "status",
            "created_at",
        )


class AdminOrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = OrderItem
        fields = ("id", "product", "product_name", "quantity", "price")


class AdminShippingAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShippingAddress
        fields = (
            "full_name",
            "phone_number",
            "address_line_1",
            "address_line_2",
            "city",
            "state",
            "postal_code",
            "country",
        )


class AdminOrderEventSerializer(serializers.ModelSerializer):
    changed_by_email = serializers.EmailField(source="changed_by.email", read_only=True)
    changed_by_name = serializers.CharField(source="changed_by.name", read_only=True)

    class Meta:
        model = OrderEvent
        fields = (
            "id",
            "previous_status",
            "new_status",
            "previous_payment_status",
            "new_payment_status",
            "note",
            "changed_by_email",
            "changed_by_name",
            "created_at",
        )


class AdminShippingEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShippingEvent
        fields = (
            "id",
            "event_type",
            "location",
            "timestamp",
        )


class AdminOrderDetailSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    user_name = serializers.CharField(source="user.name", read_only=True)
    items = AdminOrderItemSerializer(many=True, read_only=True)
    shipping_address = AdminShippingAddressSerializer(read_only=True)
    timeline = AdminOrderEventSerializer(source="events", many=True, read_only=True)
    shipping_timeline = AdminShippingEventSerializer(source="shipping_events", many=True, read_only=True)

    class Meta:
        model = Order
        fields = (
            "id",
            "user",
            "user_email",
            "user_name",
            "total_amount",
            "gross_amount",
            "coupon_discount",
            "status",
            "payment_status",
            "tracking_id",
            "shipping_provider",
            "shipped_at",
            "delivered_at",
            "created_at",
            "updated_at",
            "items",
            "shipping_address",
            "timeline",
            "shipping_timeline",
        )


class AdminOrderStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=(
            ("processing", "Processing"),
            *Order.Status.choices,
        )
    )
    payment_status = serializers.ChoiceField(choices=Order.PaymentStatus.choices, required=False)
    note = serializers.CharField(max_length=255, required=False, allow_blank=True)

    def validate_status(self, value):
        if value == "processing":
            return Order.Status.CONFIRMED
        return value


class AdminShipOrderSerializer(serializers.Serializer):
    shipping_provider = serializers.CharField(max_length=100, required=False, allow_blank=True)
    location = serializers.CharField(max_length=255, required=False, allow_blank=True)


class AdminDeliverOrderSerializer(serializers.Serializer):
    location = serializers.CharField(max_length=255, required=False, allow_blank=True)


class AdminInventoryItemSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField(source="id", read_only=True)
    active_reserved = serializers.IntegerField(read_only=True)
    available_quantity = serializers.IntegerField(read_only=True)
    last_reservation_expires_at = serializers.DateTimeField(read_only=True, allow_null=True)

    class Meta:
        model = Product
        fields = (
            "product_id",
            "sku",
            "name",
            "stock_quantity",
            "active_reserved",
            "available_quantity",
            "is_active",
            "last_reservation_expires_at",
        )


class AdminReservationSerializer(serializers.ModelSerializer):
    order_id = serializers.IntegerField(source="order.id", read_only=True)
    product_id = serializers.IntegerField(source="product.id", read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)
    order_status = serializers.CharField(source="order.status", read_only=True)
    order_payment_status = serializers.CharField(source="order.payment_status", read_only=True)

    class Meta:
        model = InventoryReservation
        fields = (
            "id",
            "order_id",
            "product_id",
            "product_name",
            "quantity",
            "status",
            "expires_at",
            "created_at",
            "order_status",
            "order_payment_status",
        )


class AdminFailedPaymentSerializer(serializers.ModelSerializer):
    order_id = serializers.IntegerField(source="order.id", read_only=True)
    user_email = serializers.EmailField(source="order.user.email", read_only=True)
    order_status = serializers.CharField(source="order.status", read_only=True)
    order_payment_status = serializers.CharField(source="order.payment_status", read_only=True)

    class Meta:
        model = Payment
        fields = (
            "id",
            "order_id",
            "user_email",
            "status",
            "failure_reason",
            "razorpay_order_id",
            "razorpay_payment_id",
            "updated_at",
            "order_status",
            "order_payment_status",
        )
