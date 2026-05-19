from django.contrib import admin

from .models import Payment, PaymentEvent, PaymentWebhookEvent, PaymentWebhookRetry


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "order",
        "razorpay_order_id",
        "razorpay_payment_id",
        "amount",
        "currency",
        "status",
        "created_at",
    )
    list_filter = ("status", "currency", "created_at", "verified_at")
    search_fields = (
        "order__id",
        "order__user__email",
        "razorpay_order_id",
        "razorpay_payment_id",
        "idempotency_key",
    )
    list_select_related = ("order", "order__user")
    readonly_fields = ("created_at", "updated_at", "verified_at")

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("order", "order__user")


@admin.register(PaymentWebhookEvent)
class PaymentWebhookEventAdmin(admin.ModelAdmin):
    list_display = ("event_id", "event_type", "processed_at")
    list_filter = ("event_type", "processed_at")
    search_fields = ("event_id", "event_type")


@admin.register(PaymentEvent)
class PaymentEventAdmin(admin.ModelAdmin):
    list_display = ("id", "payment", "event_type", "created_at")
    list_filter = ("event_type", "created_at")
    search_fields = ("payment__razorpay_order_id", "payment__razorpay_payment_id", "event_type")
    readonly_fields = ("payment", "event_type", "metadata", "created_at")
    list_select_related = ("payment", "payment__order")


@admin.register(PaymentWebhookRetry)
class PaymentWebhookRetryAdmin(admin.ModelAdmin):
    list_display = ("id", "payment", "event_id", "event_type", "attempts", "status", "next_retry_at", "updated_at")
    list_filter = ("status", "event_type", "updated_at")
    search_fields = ("event_id", "payment__razorpay_order_id", "payment__order__id")
    readonly_fields = ("created_at", "updated_at")
    list_select_related = ("payment", "payment__order")
