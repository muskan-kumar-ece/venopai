from django.urls import path

from .views import (
    AdminFailedPaymentsView,
    AdminInventoryOverviewView,
    AdminOperationsSummaryView,
    AdminReservationListView,
    AdminDeliverOrderView,
    AdminOrderDetailView,
    AdminOrderListView,
    AdminShipOrderView,
    AdminOrderStatusUpdateView,
    AnalyticsSummaryView,
)

urlpatterns = [
    path("analytics/summary/", AnalyticsSummaryView.as_view(), name="api-admin-analytics-summary"),
    path("operations/summary/", AdminOperationsSummaryView.as_view(), name="api-admin-ops-summary"),
    path("inventory/", AdminInventoryOverviewView.as_view(), name="api-admin-inventory"),
    path("reservations/", AdminReservationListView.as_view(), name="api-admin-reservations"),
    path("payments/failed/", AdminFailedPaymentsView.as_view(), name="api-admin-payments-failed"),
    path("orders/", AdminOrderListView.as_view(), name="api-admin-orders-list"),
    path("orders/<int:order_id>/", AdminOrderDetailView.as_view(), name="api-admin-orders-detail"),
    path("orders/<int:order_id>/status/", AdminOrderStatusUpdateView.as_view(), name="api-admin-orders-status"),
    path("orders/<int:order_id>/ship/", AdminShipOrderView.as_view(), name="api-admin-orders-ship"),
    path("orders/<int:order_id>/deliver/", AdminDeliverOrderView.as_view(), name="api-admin-orders-deliver"),
]
