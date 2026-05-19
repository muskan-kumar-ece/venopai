from datetime import timedelta

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from core.observability import log_event, metric_incr
from orders.cart_recovery import send_abandoned_cart_reminders
from orders.inventory import expire_stale_reservations, release_order_inventory
from orders.models import Order
from orders.notifications import send_order_email


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    retry_kwargs={"max_retries": 5},
)
def send_order_email_task(self, email_type: str, order_id: int):
    order = Order.objects.select_related("user").get(pk=order_id)
    sent = send_order_email(email_type, order)
    metric_incr("task.order_email.sent" if sent else "task.order_email.skipped")
    return {"sent": sent, "order_id": order_id, "email_type": email_type}


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    retry_kwargs={"max_retries": 5},
)
def send_abandoned_cart_reminders_task(self):
    sent_count = send_abandoned_cart_reminders()
    metric_incr("task.abandoned_cart_reminders.sent", sent_count)
    log_event("abandoned_cart_reminders_sent", sent_count=sent_count)
    return {"sent_count": sent_count}


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    retry_kwargs={"max_retries": 5},
)
def cleanup_stale_checkout_sessions_task(self):
    now = timezone.now()
    released_count = expire_stale_reservations(now=now)
    stale_orders = (
        Order.objects.select_for_update()
        .filter(
            payment_status__in=[Order.PaymentStatus.PENDING, Order.PaymentStatus.PENDING_PAYMENT],
            created_at__lt=now - timedelta(hours=2),
        )
        .distinct()
    )
    stale_count = 0
    with transaction.atomic():
        for order in stale_orders:
            stale_count += 1
            release_order_inventory(order, reason="stale_pending_order_cleanup")
    metric_incr("task.reservation_cleanup.released", released_count)
    log_event("reservation_cleanup_completed", released_count=released_count, stale_count=stale_count)
    return {"released_count": released_count, "stale_count": stale_count}
