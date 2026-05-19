from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from orders.models import Order


class Payment(models.Model):
    class Status(models.TextChoices):
        CREATED = "created", "Created"
        AUTHORIZED = "authorized", "Authorized"
        CAPTURED = "captured", "Captured"
        FAILED = "failed", "Failed"
        REFUNDED = "refunded", "Refunded"

    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="payments")
    idempotency_key = models.CharField(max_length=100, unique=True)
    razorpay_order_id = models.CharField(max_length=255, unique=True)
    razorpay_payment_id = models.CharField(max_length=255, blank=True, null=True, unique=True)
    razorpay_signature = models.CharField(max_length=255, blank=True)
    amount = models.PositiveBigIntegerField(help_text="Amount in paise")
    currency = models.CharField(max_length=10, default="INR")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.CREATED, db_index=True)
    failure_reason = models.TextField(blank=True)
    raw_response = models.JSONField(default=dict, blank=True)
    verified_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["order"]),
            models.Index(fields=["status"]),
            models.Index(fields=["order", "status"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["order"],
                condition=Q(status="captured"),
                name="unique_captured_payment_per_order",
            ),
        ]

    def __str__(self):
        return f"{self.razorpay_order_id} ({self.status})"


class PaymentWebhookEvent(models.Model):
    event_id = models.CharField(max_length=255, unique=True)
    event_type = models.CharField(max_length=100)
    processed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["event_type", "processed_at"]),
            models.Index(fields=["processed_at"]),
        ]

    def __str__(self):
        return self.event_id


class PaymentEvent(models.Model):
    class EventType(models.TextChoices):
        CREATED = "created", "Created"
        VERIFIED = "verified", "Verified"
        FAILED = "failed", "Failed"
        DUPLICATE = "duplicate", "Duplicate"
        REFUNDED = "refunded", "Refunded"
        REPLAY = "replay", "Replay"
        RETRY_ATTEMPT = "retry_attempt", "Retry Attempt"
        PAYMENT_FAILED = "payment_failed", "Payment Failed"
        PAYMENT_SUCCESS = "payment_success", "Payment Success"

    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name="events")
    event_type = models.CharField(max_length=30, choices=EventType.choices)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                check=Q(id__isnull=False),
                name="prevent_update",
            )
        ]

    def save(self, *args, **kwargs):
        if self.pk and PaymentEvent.objects.filter(pk=self.pk).exists():
            raise ValidationError("PaymentEvent is immutable and cannot be updated.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("PaymentEvent is immutable and cannot be deleted.")


class PaymentWebhookRetry(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        SUCCESS = "success", "Success"
        DEAD_LETTER = "dead_letter", "Dead Letter"

    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name="webhook_retries")
    event_id = models.CharField(max_length=255, db_index=True)
    event_type = models.CharField(max_length=100)
    payload = models.JSONField(default=dict, blank=True)
    attempts = models.PositiveIntegerField(default=0)
    max_attempts = models.PositiveIntegerField(default=5)
    next_retry_at = models.DateTimeField(db_index=True)
    last_error = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["status", "next_retry_at"]),
            models.Index(fields=["payment", "status"]),
        ]
