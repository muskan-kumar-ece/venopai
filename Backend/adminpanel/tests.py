from datetime import timedelta
from decimal import Decimal

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework.throttling import SimpleRateThrottle

from orders.admin import OrderAdmin, mark_orders_confirmed
from orders.inventory import reserve_order_inventory
from orders.models import InventoryReservation, Order, OrderItem
from payments.models import Payment
from products.models import Category, Inventory, Product
from users.models import Referral


class AdminDashboardTests(TestCase):
    def setUp(self):
        self.admin_user = get_user_model().objects.create_superuser(
            email="admin@example.com",
            password="SecurePass123!",
            name="Admin",
        )
        self.client.force_login(self.admin_user)

    def test_dashboard_metrics_with_date_range(self):
        inside_order = Order.objects.create(
            user=self.admin_user,
            total_amount=Decimal("100.00"),
            payment_status=Order.PaymentStatus.PAID,
        )
        outside_order = Order.objects.create(
            user=self.admin_user,
            total_amount=Decimal("200.00"),
            payment_status=Order.PaymentStatus.PAID,
        )
        Order.objects.filter(id=inside_order.id).update(created_at=timezone.now() - timedelta(days=1))
        Order.objects.filter(id=outside_order.id).update(created_at=timezone.now() - timedelta(days=45))

        category = Category.objects.create(name="Laptops")
        product = Product.objects.create(
            category=category,
            name="Notebook",
            description="thin",
            price=Decimal("999.00"),
            sku="NB-1",
            stock_quantity=2,
            is_refurbished=False,
            condition_grade="A",
        )
        Inventory.objects.create(product=product, quantity=2, reserved_quantity=1, reorder_level=2)

        today = timezone.localdate()
        start = (today - timedelta(days=7)).isoformat()
        end = today.isoformat()
        response = self.client.get(f"/admin/?start_date={start}&end_date={end}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["dashboard_total_orders"], 1)
        self.assertEqual(response.context["dashboard_revenue"], Decimal("100"))
        self.assertEqual(response.context["dashboard_low_stock_count"], 1)


class OrderAdminActionTests(TestCase):
    def test_mark_orders_confirmed_action(self):
        user = get_user_model().objects.create_user(
            email="buyer@example.com",
            password="SecurePass123!",
            name="Buyer",
        )
        order = Order.objects.create(user=user, total_amount=Decimal("550.00"), status=Order.Status.PENDING)

        admin_instance = OrderAdmin(Order, AdminSite())
        queryset = Order.objects.filter(id=order.id)
        mark_orders_confirmed(admin_instance, None, queryset)

        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.CONFIRMED)


class AnalyticsSummaryAPITests(TestCase):
    def setUp(self):
        self.admin_user = get_user_model().objects.create_superuser(
            email="founder@example.com",
            password="SecurePass123!",
            name="Founder",
        )
        self.regular_user = get_user_model().objects.create_user(
            email="user@example.com",
            password="SecurePass123!",
            name="User",
        )
        self.client = APIClient()

    def test_admin_can_view_analytics_summary(self):
        Referral.objects.create(referrer=self.admin_user, referred_user=self.regular_user, reward_issued=True)
        paid_order = Order.objects.create(
            user=self.regular_user,
            total_amount=Decimal("100.00"),
            gross_amount=Decimal("120.00"),
            coupon_discount=Decimal("20.00"),
            payment_status=Order.PaymentStatus.PAID,
        )
        today_refunded = Order.objects.create(
            user=self.regular_user,
            total_amount=Decimal("50.00"),
            payment_status=Order.PaymentStatus.REFUNDED,
        )
        old_paid_order = Order.objects.create(
            user=self.regular_user,
            total_amount=Decimal("200.00"),
            gross_amount=Decimal("200.00"),
            coupon_discount=Decimal("0.00"),
            payment_status=Order.PaymentStatus.PAID,
        )
        Order.objects.create(
            user=self.admin_user,
            total_amount=Decimal("500.00"),
            payment_status=Order.PaymentStatus.PAID,
        )
        Order.objects.filter(id=paid_order.id).update(created_at=timezone.now())
        Order.objects.filter(id=today_refunded.id).update(created_at=timezone.now())
        Order.objects.filter(id=old_paid_order.id).update(created_at=timezone.now() - timedelta(days=10))

        self.client.force_authenticate(self.admin_user)
        response = self.client.get("/admin/analytics/summary/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_revenue"], "800.00")
        self.assertEqual(response.data["gross_revenue"], "820.00")
        self.assertEqual(response.data["discount_amount"], "20.00")
        self.assertEqual(response.data["net_revenue"], "800.00")
        self.assertEqual(response.data["total_orders"], 4)
        self.assertEqual(response.data["total_paid_orders"], 3)
        self.assertEqual(response.data["total_refunded_orders"], 1)
        self.assertEqual(response.data["total_referrals"], 1)
        self.assertEqual(response.data["successful_referrals"], 1)
        self.assertEqual(response.data["revenue_from_referrals"], "300.00")
        self.assertEqual(response.data["refund_rate_percent"], 25.0)
        self.assertEqual(response.data["today_revenue"], "600.00")
        self.assertEqual(response.data["today_orders"], 3)
        self.assertEqual(response.data["last_7_days_revenue"], "600.00")

    def test_non_admin_cannot_view_analytics_summary(self):
        self.client.force_authenticate(self.regular_user)
        response = self.client.get("/admin/analytics/summary/")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_referral_without_paid_order_has_zero_referral_revenue(self):
        pending_user = get_user_model().objects.create_user(
            email="pending-ref@example.com",
            password="SecurePass123!",
            name="Pending Referral",
        )
        Referral.objects.create(referrer=self.admin_user, referred_user=pending_user, reward_issued=False)

        self.client.force_authenticate(self.admin_user)
        response = self.client.get("/admin/analytics/summary/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["revenue_from_referrals"], "0.00")

    def test_admin_endpoint_is_rate_limited(self):
        cache.clear()
        original_rates = SimpleRateThrottle.THROTTLE_RATES.copy()
        SimpleRateThrottle.THROTTLE_RATES["admin"] = "1/minute"
        try:
            self.client.force_authenticate(self.admin_user)
            self.assertEqual(self.client.get("/admin/analytics/summary/").status_code, status.HTTP_200_OK)
            self.assertEqual(
                self.client.get("/admin/analytics/summary/").status_code,
                status.HTTP_429_TOO_MANY_REQUESTS,
            )
        finally:
            SimpleRateThrottle.THROTTLE_RATES = original_rates
            cache.clear()


class AdminOperationsVisibilityTests(TestCase):
    def setUp(self):
        self.admin_user = get_user_model().objects.create_superuser(
            email="ops-admin@example.com",
            password="SecurePass123!",
            name="Ops Admin",
        )
        self.regular_user = get_user_model().objects.create_user(
            email="ops-user@example.com",
            password="SecurePass123!",
            name="Ops User",
        )
        self.client = APIClient()
        self.category = Category.objects.create(name="Ops Category")
        self.product = Product.objects.create(
            category=self.category,
            name="Ops Product",
            description="Ops",
            price=Decimal("1500.00"),
            sku="OPS-001",
            stock_quantity=4,
        )
        self.order = Order.objects.create(
            user=self.regular_user,
            total_amount=Decimal("1500.00"),
        )
        OrderItem.objects.create(order=self.order, product=self.product, quantity=1, price=self.product.price)
        reserve_order_inventory(self.order)
        Payment.objects.create(
            order=self.order,
            idempotency_key="idem-failed",
            razorpay_order_id="order_failed_1",
            amount=150000,
            status=Payment.Status.FAILED,
            failure_reason="gateway_timeout",
        )

    def test_admin_can_view_operations_summary(self):
        self.client.force_authenticate(self.admin_user)
        response = self.client.get("/api/v1/admin/operations/summary/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["active_reservations"], 1)
        self.assertEqual(response.data["failed_payments"], 1)

    def test_admin_can_list_inventory_overview(self):
        self.client.force_authenticate(self.admin_user)
        response = self.client.get("/api/v1/admin/inventory/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        item = response.data["results"][0]
        self.assertEqual(item["product_id"], self.product.id)
        self.assertEqual(item["active_reserved"], 1)
        self.assertEqual(item["available_quantity"], 3)

    def test_admin_can_list_reservations(self):
        self.client.force_authenticate(self.admin_user)
        response = self.client.get("/api/v1/admin/reservations/", {"status": "active"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        reservation = response.data["results"][0]
        self.assertEqual(reservation["order_id"], self.order.id)
        self.assertEqual(reservation["product_id"], self.product.id)
        self.assertEqual(reservation["status"], InventoryReservation.Status.ACTIVE)

    def test_admin_can_list_failed_payments(self):
        self.client.force_authenticate(self.admin_user)
        response = self.client.get("/api/v1/admin/payments/failed/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        payment = response.data["results"][0]
        self.assertEqual(payment["order_id"], self.order.id)
        self.assertEqual(payment["status"], Payment.Status.FAILED)

    def test_non_admin_cannot_access_operations_endpoints(self):
        self.client.force_authenticate(self.regular_user)
        endpoints = [
            "/api/v1/admin/operations/summary/",
            "/api/v1/admin/inventory/",
            "/api/v1/admin/reservations/",
            "/api/v1/admin/payments/failed/",
        ]
        for endpoint in endpoints:
            response = self.client.get(endpoint)
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
