from django.contrib import admin
from django.contrib import messages
from django.db.models import DecimalField, F, Sum, Value
from django.db.models.functions import Coalesce
from django.utils.dateparse import parse_date
from django.utils import timezone

from orders.models import Order
from products.models import Inventory

DEFAULT_DASHBOARD_DAYS = 30


def _dashboard_date_range(request):
    start_raw = request.GET.get("start_date", "")
    end_raw = request.GET.get("end_date", "")
    parsed_start = parse_date(start_raw) if start_raw else None
    parsed_end = parse_date(end_raw) if end_raw else None

    end_date = parsed_end or timezone.localdate()
    start_date = parsed_start if start_raw else (end_date - timezone.timedelta(days=DEFAULT_DASHBOARD_DAYS))
    if start_raw and not parsed_start:
        start_date = end_date - timezone.timedelta(days=DEFAULT_DASHBOARD_DAYS)
        messages.warning(request, "Invalid start date. Showing default range.")
    if end_raw and not parsed_end:
        messages.warning(request, "Invalid end date. Showing default range.")
    if start_date > end_date:
        start_date, end_date = end_date, start_date
        messages.warning(request, "Start date was after end date, so the range was swapped.")
    return start_date, end_date


def _dashboard_context(request):
    start_date, end_date = _dashboard_date_range(request)
    order_queryset = Order.objects.filter(created_at__date__gte=start_date, created_at__date__lte=end_date)
    revenue = order_queryset.filter(payment_status=Order.PaymentStatus.PAID).aggregate(
        total=Coalesce(Sum("total_amount"), Value(0, output_field=DecimalField(max_digits=12, decimal_places=2)))
    )["total"]
    low_stock_queryset = (
        Inventory.objects.select_related("product")
        .annotate(available=F("quantity") - F("reserved_quantity"))
        .filter(available__lt=F("reorder_level"))
        .order_by("available")
    )
    return {
        "dashboard_total_orders": order_queryset.count(),
        "dashboard_pending_orders": order_queryset.filter(
            status__in=[Order.Status.PENDING, Order.Status.PENDING_PAYMENT, Order.Status.PAYMENT_PROCESSING]
        ).count(),
        "dashboard_revenue": revenue,
        "dashboard_start_date": start_date.isoformat(),
        "dashboard_end_date": end_date.isoformat(),
        "dashboard_low_stock_items": low_stock_queryset[:5],
        "dashboard_low_stock_count": low_stock_queryset.count(),
    }


_default_admin_index = admin.site.index


def _custom_admin_index(request, extra_context=None):
    context = extra_context or {}
    context.update(_dashboard_context(request))
    return _default_admin_index(request, extra_context=context)


admin.site.site_header = "Ecommerce Enterprise Admin"
admin.site.site_title = "Ecommerce Admin"
admin.site.index_title = "Operations Dashboard"
admin.site.index_template = "adminpanel/index.html"
admin.site.index = _custom_admin_index
