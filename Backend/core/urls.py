from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from django.conf import settings

from adminpanel.views import (
    AdminDeliverOrderView,
    AdminOrderDetailView,
    AdminOrderListView,
    AdminShipOrderView,
    AdminOrderStatusUpdateView,
    AnalyticsSummaryView,
)

urlpatterns = [
    # Backward-compatible admin-panel API routes (unversioned).
    # These MUST appear before path("admin/", ...) so they are not swallowed by
    # the Django admin catch-all. Canonical versions live under /api/v1/admin/.
    path("admin/analytics/summary/", AnalyticsSummaryView.as_view(), name="analytics-summary"),
    path("admin/orders/", AdminOrderListView.as_view(), name="admin-orders-list"),
    path("admin/orders/<int:order_id>/", AdminOrderDetailView.as_view(), name="admin-orders-detail"),
    path("admin/orders/<int:order_id>/status/", AdminOrderStatusUpdateView.as_view(), name="admin-orders-status"),
    path("admin/orders/<int:order_id>/ship/", AdminShipOrderView.as_view(), name="admin-orders-ship"),
    path("admin/orders/<int:order_id>/deliver/", AdminDeliverOrderView.as_view(), name="admin-orders-deliver"),

    # Django admin UI (must come after the API routes above)
    path(getattr(settings, "ADMIN_URL_PATH", "admin/"), admin.site.urls),

    # Versioned REST API
    path("api/v1/", include("core.api_urls")),

    # OpenAPI schema + interactive docs (restrict access in production)
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]
