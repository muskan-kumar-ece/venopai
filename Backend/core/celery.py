import os
import logging

from celery import Celery
from celery.schedules import crontab
from celery.signals import task_failure, task_postrun, task_prerun
from django.conf import settings

from core.observability import log_event, metric_incr, metric_observe_ms

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings.dev")

app = Celery("core")
app.config_from_object("django.conf:settings", namespace="CELERY")

app.conf.update(
    broker_url=settings.CELERY_BROKER_URL,
    result_backend=settings.CELERY_RESULT_BACKEND,
    task_serializer="json",
    accept_content=["json"],
    timezone=settings.TIME_ZONE,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
)

app.conf.beat_schedule = {
    "orders.send-abandoned-cart-reminders": {
        "task": "orders.tasks.send_abandoned_cart_reminders_task",
        "schedule": crontab(minute="*/30"),
    },
    "orders.cleanup-reservations": {
        "task": "orders.tasks.cleanup_stale_checkout_sessions_task",
        "schedule": crontab(minute="*/10"),
    },
    "payments.reconcile-pending-payments": {
        "task": "payments.tasks.reconcile_pending_payments_task",
        "schedule": crontab(minute="*/15"),
    },
    "payments.retry-webhook-processing": {
        "task": "payments.tasks.retry_webhook_processing_task",
        "schedule": crontab(minute="*/5"),
    },
    "admin.aggregate-analytics-cache": {
        "task": "adminpanel.tasks.aggregate_analytics_cache_task",
        "schedule": crontab(minute="*/10"),
    },
}

app.autodiscover_tasks()

logger = logging.getLogger(__name__)
_task_starts: dict[str, float] = {}


@task_prerun.connect
def on_task_prerun(task_id=None, task=None, **kwargs):
    _task_starts[task_id] = __import__("time").monotonic()
    metric_incr("task.started")
    log_event("task_started", task_name=getattr(task, "name", "unknown"), task_id=task_id)


@task_postrun.connect
def on_task_postrun(task_id=None, task=None, state=None, **kwargs):
    started = _task_starts.pop(task_id, None)
    if started is not None:
        duration_ms = (__import__("time").monotonic() - started) * 1000
        metric_observe_ms("task.runtime", duration_ms)
    metric_incr(f"task.state.{(state or 'unknown').lower()}")
    log_event("task_completed", task_name=getattr(task, "name", "unknown"), task_id=task_id, state=state)


@task_failure.connect
def on_task_failure(task_id=None, exception=None, sender=None, **kwargs):
    metric_incr("task.failed")
    logger.exception("task_failed task=%s task_id=%s error=%s", getattr(sender, "name", "unknown"), task_id, exception)
