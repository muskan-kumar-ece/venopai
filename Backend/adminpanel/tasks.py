from datetime import timedelta
from decimal import Decimal

from celery import shared_task
from django.core.cache import cache
from django.db.models import Count, Q, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from core.observability import log_event, metric_incr
from orders.models import Order, OrderItem


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
)
def aggregate_analytics_cache_task(self):
    total_orders = Order.objects.count()
    total_revenue = (
        Order.objects.filter(payment_status=Order.PaymentStatus.PAID).aggregate(
            total=Coalesce(Sum("total_amount"), Decimal("0.00"))
        )["total"]
    )
    top_products = list(
        OrderItem.objects.filter(order__payment_status=Order.PaymentStatus.PAID)
        .values("product_id", "product__name")
        .annotate(total_sold=Coalesce(Sum("quantity"), 0))
        .order_by("-total_sold", "product_id")[:5]
    )
    today = timezone.localdate()
    snapshot = {
        "total_orders": total_orders,
        "total_revenue": f"{total_revenue:.2f}",
        "total_paid_orders": Order.objects.filter(payment_status=Order.PaymentStatus.PAID).count(),
        "total_refunded_orders": Order.objects.filter(payment_status=Order.PaymentStatus.REFUNDED).count(),
        "today_orders": Order.objects.filter(created_at__date=today).count(),
        "today_revenue": f"{Order.objects.filter(payment_status=Order.PaymentStatus.PAID, created_at__date=today).aggregate(total=Coalesce(Sum('total_amount'), Decimal('0.00')))['total']:.2f}",
        "last_7_days_orders": Order.objects.filter(created_at__date__gte=today - timedelta(days=6)).count(),
        "top_products": top_products,
    }
    cache.set("admin_analytics_summary", snapshot, timeout=600)
    metric_incr("task.analytics_aggregate.success")
    log_event("analytics_cache_aggregated", total_orders=total_orders)
    return snapshot
