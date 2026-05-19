from datetime import timedelta

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from core.observability import log_event, metric_incr
from orders.inventory import release_order_inventory
from orders.models import Order
from payments.models import Payment, PaymentWebhookRetry


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    retry_kwargs={"max_retries": 5},
)
def reconcile_pending_payments_task(self):
    cutoff = timezone.now() - timedelta(minutes=30)
    stale = Payment.objects.select_related("order").filter(
        status=Payment.Status.CREATED,
        order__payment_status__in=[Order.PaymentStatus.PENDING, Order.PaymentStatus.PENDING_PAYMENT],
        created_at__lt=cutoff,
    )[:200]
    flagged = 0
    for payment in stale:
        flagged += 1
        payment.order.payment_status = Order.PaymentStatus.FAILED
        payment.order.status = Order.Status.FAILED
        payment.order.save(update_fields=["payment_status", "status", "updated_at"])
        release_order_inventory(payment.order, reason="payment_reconciliation_timeout", payment_reference=payment.razorpay_order_id)
    metric_incr("task.payment_reconcile.flagged", flagged)
    log_event("payment_reconciliation_completed", flagged=flagged)
    return {"flagged": flagged}


@shared_task(bind=True, max_retries=5)
def retry_webhook_processing_task(self):
    now = timezone.now()
    candidates = (
        PaymentWebhookRetry.objects.select_for_update()
        .filter(status=PaymentWebhookRetry.Status.PENDING, next_retry_at__lte=now)
        .order_by("next_retry_at")[:100]
    )
    processed = 0
    with transaction.atomic():
        for retry in candidates:
            processed += 1
            retry.status = PaymentWebhookRetry.Status.PROCESSING
            retry.attempts += 1
            retry.save(update_fields=["status", "attempts", "updated_at"])
            try:
                # Reconciliation strategy: if payment eventually captured/failed, mark success.
                payment = retry.payment
                if payment.status in {Payment.Status.CAPTURED, Payment.Status.FAILED, Payment.Status.REFUNDED}:
                    retry.status = PaymentWebhookRetry.Status.SUCCESS
                    retry.save(update_fields=["status", "updated_at"])
                    metric_incr("task.webhook_retry.success")
                    continue
                raise RuntimeError("Payment still in transitional state")
            except Exception as exc:  # noqa: BLE001
                retry.last_error = str(exc)
                if retry.attempts >= retry.max_attempts:
                    retry.status = PaymentWebhookRetry.Status.DEAD_LETTER
                    metric_incr("task.webhook_retry.dead_letter")
                else:
                    retry.status = PaymentWebhookRetry.Status.PENDING
                    backoff_minutes = min(2 ** retry.attempts, 60)
                    retry.next_retry_at = now + timedelta(minutes=backoff_minutes)
                retry.save(update_fields=["status", "last_error", "next_retry_at", "updated_at"])
    metric_incr("task.webhook_retry.processed", processed)
    log_event("webhook_retry_completed", processed=processed)
    return {"processed": processed}
