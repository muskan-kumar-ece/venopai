from decimal import Decimal
from datetime import timedelta
import time
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from django.core import mail
from django.test import TestCase
from django.test.utils import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient, APIRequestFactory, force_authenticate
from rest_framework.throttling import SimpleRateThrottle

from products.models import Category, Product
from payments.models import Payment

from .cart_recovery import send_abandoned_cart_reminders
from .inventory import expire_stale_reservations, reserve_order_inventory
from .models import (
    Cart,
    Coupon,
    CouponUsage,
    EmailEvent,
    InventoryReservation,
    Order,
    OrderEvent,
    OrderItem,
    ShippingAddress,
    ShippingEvent,
)
from .notifications import send_order_email
from .tasks import cleanup_stale_checkout_sessions_task
from .views import OrderViewSet


class OrderModelTests(TestCase):
    def test_order_defaults(self):
        user = get_user_model().objects.create_user(
            email="buyer@example.com",
            password="StrongPass123",
            name="Buyer",
        )
        order = Order.objects.create(user=user, total_amount=Decimal("1200.00"))

        self.assertEqual(order.status, Order.Status.PENDING)
        self.assertEqual(order.payment_status, Order.PaymentStatus.PENDING)


class OrderAPITests(TestCase):
    def test_orders_list_requires_authentication(self):
        client = APIClient()
        response = client.get("/api/v1/orders/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_user_can_create_order(self):
        user = get_user_model().objects.create_user(
            email="student@example.com",
            password="StrongPass123",
            name="Student",
        )
        category = Category.objects.create(name="Accessories")
        Product.objects.create(
            category=category,
            name="Mouse",
            description="Wireless mouse",
            price=Decimal("999.00"),
            sku="MSE-001",
            stock_quantity=20,
            is_refurbished=False,
            condition_grade="A",
        )

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post("/api/v1/orders/", {"total_amount": "999.00"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_cart_item_create_rejects_other_users_cart(self):
        user = get_user_model().objects.create_user(
            email="buyer1@example.com",
            password="StrongPass123",
            name="Buyer 1",
        )
        other_user = get_user_model().objects.create_user(
            email="buyer2@example.com",
            password="StrongPass123",
            name="Buyer 2",
        )
        category = Category.objects.create(name="Audio")
        product = Product.objects.create(
            category=category,
            name="Headphones",
            description="Noise cancelling",
            price=Decimal("2499.00"),
            sku="AUD-001",
            stock_quantity=10,
            is_refurbished=False,
            condition_grade="A",
        )
        other_cart = Cart.objects.create(user=other_user)

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post(
            "/api/v1/orders/cart-items/",
            {"cart": other_cart.id, "product": product.id, "quantity": 1},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_order_create_is_idempotent_for_same_header_key(self):
        user = get_user_model().objects.create_user(
            email="idempotent@example.com",
            password="StrongPass123",
            name="Idempotent",
        )
        factory = APIRequestFactory()
        view = OrderViewSet.as_view({"post": "create"})
        payload = {"total_amount": "499.00"}
        first_request = factory.post(
            "/api/v1/orders/",
            payload,
            format="json",
            headers={"Idempotency-Key": "order-key-1"},
        )
        force_authenticate(first_request, user=user)
        first_response = view(first_request)
        second_request = factory.post(
            "/api/v1/orders/",
            payload,
            format="json",
            headers={"Idempotency-Key": "order-key-1"},
        )
        force_authenticate(second_request, user=user)
        second_response = view(second_request)

        self.assertEqual(first_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Order.objects.get(id=first_response.data["id"]).idempotency_key, "order-key-1")
        self.assertEqual(first_response.data["id"], second_response.data["id"])
        self.assertEqual(Order.objects.filter(user=user, idempotency_key="order-key-1").count(), 1)

    @patch("orders.views.send_order_email_task.delay")
    def test_customer_can_cancel_non_shipped_order(self, mock_delay):
        user = get_user_model().objects.create_user(
            email="canceluser@example.com",
            password="StrongPass123",
            name="Cancel User",
        )
        order = Order.objects.create(user=user, total_amount=Decimal("499.00"), status=Order.Status.PENDING)
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.post(f"/api/v1/orders/{order.id}/cancel/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.CANCELLED)
        self.assertTrue(order.events.filter(new_status=Order.Status.CANCELLED).exists())
        mock_delay.assert_called_once_with("order_cancelled", order.id)

    def test_customer_cannot_cancel_shipped_order(self):
        user = get_user_model().objects.create_user(
            email="shippeduser@example.com",
            password="StrongPass123",
            name="Shipped User",
        )
        order = Order.objects.create(user=user, total_amount=Decimal("499.00"), status=Order.Status.SHIPPED)
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.post(f"/api/v1/orders/{order.id}/cancel/")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.SHIPPED)


class OrderCreateWithItemsAPITests(TestCase):
    """Tests for the new create order with items endpoint."""

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="orderuser@example.com",
            password="StrongPass123",
            name="Order User",
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        
        # Create test products
        self.category = Category.objects.create(name="Electronics")
        self.product1 = Product.objects.create(
            category=self.category,
            name="Laptop",
            description="Gaming laptop",
            price=Decimal("50000.00"),
            sku="LAP-001",
            stock_quantity=10,
        )
        self.product2 = Product.objects.create(
            category=self.category,
            name="Mouse",
            description="Wireless mouse",
            price=Decimal("1500.00"),
            sku="MSE-001",
            stock_quantity=20,
        )

    def test_create_order_with_items(self):
        """Test creating an order with multiple items."""
        response = self.client.post(
            "/api/v1/orders/create/",
            {
                "items": [
                    {"product_id": self.product1.id, "quantity": 1},
                    {"product_id": self.product2.id, "quantity": 2},
                ]
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("id", response.data)
        self.assertIn("items", response.data)
        self.assertEqual(len(response.data["items"]), 2)
        expected_total = str(self.product1.price * 1 + self.product2.price * 2)
        self.assertEqual(response.data["total_amount"], expected_total)
        self.assertEqual(response.data["status"], Order.Status.PENDING)
        self.assertEqual(response.data["payment_status"], Order.PaymentStatus.PENDING)

        # Verify order was created in database
        order = Order.objects.get(id=response.data["id"])
        self.assertEqual(order.user, self.user)
        self.assertEqual(order.items.count(), 2)

    def test_create_order_with_single_item(self):
        """Test creating an order with a single item."""
        response = self.client.post(
            "/api/v1/orders/create/",
            {
                "items": [
                    {"product_id": self.product1.id, "quantity": 2},
                ]
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        expected_total = str(self.product1.price * 2)
        self.assertEqual(response.data["total_amount"], expected_total)
        self.assertEqual(len(response.data["items"]), 1)
        self.assertEqual(response.data["items"][0]["quantity"], 2)
        self.assertEqual(response.data["items"][0]["price"], str(self.product1.price))

    def test_create_order_requires_authentication(self):
        """Test that creating an order requires authentication."""
        client = APIClient()
        response = client.post(
            "/api/v1/orders/create/",
            {
                "items": [
                    {"product_id": self.product1.id, "quantity": 1},
                ]
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_order_requires_items(self):
        """Test that items are required to create an order."""
        response = self.client.post(
            "/api/v1/orders/create/",
            {"items": []},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("items", response.data)

    def test_create_order_endpoint_is_rate_limited(self):
        cache.clear()
        original_rates = SimpleRateThrottle.THROTTLE_RATES.copy()
        SimpleRateThrottle.THROTTLE_RATES["order_create"] = "2/minute"
        try:
            payload = {"items": [{"product_id": self.product1.id, "quantity": 1}]}
            self.assertEqual(self.client.post("/api/v1/orders/create/", payload, format="json").status_code, status.HTTP_201_CREATED)
            self.assertEqual(self.client.post("/api/v1/orders/create/", payload, format="json").status_code, status.HTTP_201_CREATED)
            self.assertEqual(
                self.client.post("/api/v1/orders/create/", payload, format="json").status_code,
                status.HTTP_429_TOO_MANY_REQUESTS,
            )
        finally:
            SimpleRateThrottle.THROTTLE_RATES = original_rates
            cache.clear()

    def test_create_order_with_invalid_product(self):
        """Test creating an order with a non-existent product."""
        response = self.client.post(
            "/api/v1/orders/create/",
            {
                "items": [
                    {"product_id": 99999, "quantity": 1},
                ]
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_order_with_inactive_product(self):
        """Test creating an order with an inactive product."""
        self.product1.is_active = False
        self.product1.save()

        response = self.client.post(
            "/api/v1/orders/create/",
            {
                "items": [
                    {"product_id": self.product1.id, "quantity": 1},
                ]
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_my_orders_endpoint(self):
        """Test the my-orders endpoint."""
        # Create some orders
        order1 = Order.objects.create(user=self.user, total_amount=Decimal("1000.00"))
        order2 = Order.objects.create(user=self.user, total_amount=Decimal("2000.00"))
        
        # Create orders for another user
        other_user = get_user_model().objects.create_user(
            email="other@example.com",
            password="StrongPass123",
            name="Other User",
        )
        Order.objects.create(user=other_user, total_amount=Decimal("3000.00"))

        response = self.client.get("/api/v1/orders/my-orders/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)
        order_ids = [order["id"] for order in response.data["results"]]
        self.assertIn(order1.id, order_ids)
        self.assertIn(order2.id, order_ids)

    def test_my_orders_requires_authentication(self):
        """Test that my-orders requires authentication."""
        client = APIClient()
        response = client.get("/api/v1/orders/my-orders/")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_order_detail_includes_items(self):
        """Test that order detail endpoint includes items."""
        order = Order.objects.create(user=self.user, total_amount=Decimal("51500.00"))
        OrderItem.objects.create(order=order, product=self.product1, quantity=1, price=self.product1.price)
        OrderItem.objects.create(order=order, product=self.product2, quantity=1, price=self.product2.price)

        response = self.client.get(f"/api/v1/orders/{order.id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("items", response.data)
        self.assertEqual(len(response.data["items"]), 2)

    def test_order_detail_includes_shipping_timeline_fields(self):
        order = Order.objects.create(
            user=self.user,
            total_amount=Decimal("1000.00"),
            tracking_id="TRK-123",
            shipping_provider="BlueDart",
            shipped_at=timezone.now() - timedelta(days=1),
            delivered_at=timezone.now(),
            status=Order.Status.DELIVERED,
            payment_status=Order.PaymentStatus.PAID,
        )
        ShippingEvent.objects.create(
            order=order,
            event_type=ShippingEvent.EventType.IN_TRANSIT,
            location="Delhi Hub",
        )

        response = self.client.get(f"/api/v1/orders/{order.id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["tracking_id"], "TRK-123")
        self.assertEqual(response.data["shipping_provider"], "BlueDart")
        self.assertIn("shipped_at", response.data)
        self.assertIn("delivered_at", response.data)
        self.assertIn("shipping_events", response.data)
        self.assertEqual(len(response.data["shipping_events"]), 1)


class CouponAPITests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="couponuser@example.com",
            password="StrongPass123",
            name="Coupon User",
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        now = timezone.now()
        self.coupon = Coupon.objects.create(
            code="SAVE10",
            discount_type=Coupon.DiscountType.PERCENTAGE,
            discount_value=Decimal("10.00"),
            minimum_order_amount=Decimal("500.00"),
            max_uses=2,
            per_user_limit=1,
            valid_from=now - timedelta(days=1),
            valid_until=now + timedelta(days=1),
            is_active=True,
        )

    def test_apply_coupon_updates_order_amounts_and_usage(self):
        order = Order.objects.create(user=self.user, total_amount=Decimal("1000.00"))

        response = self.client.post(
            f"/api/v1/orders/{order.id}/apply-coupon/",
            {"code": "save10"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        order.refresh_from_db()
        self.coupon.refresh_from_db()
        self.assertEqual(order.gross_amount, Decimal("1000.00"))
        self.assertEqual(order.coupon_discount, Decimal("100.00"))
        self.assertEqual(order.total_amount, Decimal("900.00"))
        self.assertEqual(order.applied_coupon_id, self.coupon.id)
        self.assertEqual(self.coupon.used_count, 1)
        self.assertEqual(CouponUsage.objects.filter(coupon=self.coupon, user=self.user, order=order).count(), 1)

    def test_apply_coupon_is_idempotent_when_same_coupon_is_reused(self):
        order = Order.objects.create(user=self.user, total_amount=Decimal("1000.00"))

        first = self.client.post(f"/api/v1/orders/{order.id}/apply-coupon/", {"code": "SAVE10"}, format="json")
        second = self.client.post(f"/api/v1/orders/{order.id}/apply-coupon/", {"code": "SAVE10"}, format="json")

        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.coupon.refresh_from_db()
        self.assertEqual(self.coupon.used_count, 1)
        self.assertEqual(CouponUsage.objects.filter(coupon=self.coupon, order=order).count(), 1)

    def test_apply_coupon_rejects_per_user_limit_and_minimum_amount(self):
        first_order = Order.objects.create(user=self.user, total_amount=Decimal("1000.00"))
        self.client.post(f"/api/v1/orders/{first_order.id}/apply-coupon/", {"code": "SAVE10"}, format="json")

        second_order = Order.objects.create(user=self.user, total_amount=Decimal("1000.00"))
        per_user_limit_response = self.client.post(
            f"/api/v1/orders/{second_order.id}/apply-coupon/",
            {"code": "SAVE10"},
            format="json",
        )
        self.assertEqual(per_user_limit_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Per-user coupon usage limit exceeded.", str(per_user_limit_response.data))

        low_amount_order = Order.objects.create(user=self.user, total_amount=Decimal("200.00"))
        low_amount_response = self.client.post(
            f"/api/v1/orders/{low_amount_order.id}/apply-coupon/",
            {"code": "SAVE10"},
            format="json",
        )
        self.assertEqual(low_amount_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("minimum amount", str(low_amount_response.data))

    def test_apply_coupon_rejects_expired_and_max_use_limit(self):
        max_use_coupon = Coupon.objects.create(
            code="MAXED",
            discount_type=Coupon.DiscountType.FIXED,
            discount_value=Decimal("50.00"),
            max_uses=1,
            used_count=1,
            valid_from=timezone.now() - timedelta(days=2),
            valid_until=timezone.now() + timedelta(days=2),
            is_active=True,
        )
        order = Order.objects.create(user=self.user, total_amount=Decimal("1000.00"))
        maxed_response = self.client.post(
            f"/api/v1/orders/{order.id}/apply-coupon/",
            {"code": max_use_coupon.code},
            format="json",
        )
        self.assertEqual(maxed_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("usage limit exceeded", str(maxed_response.data))

        expired_coupon = Coupon.objects.create(
            code="EXPIRED",
            discount_type=Coupon.DiscountType.FIXED,
            discount_value=Decimal("50.00"),
            valid_from=timezone.now() - timedelta(days=5),
            valid_until=timezone.now() - timedelta(days=1),
            is_active=True,
        )
        expired_response = self.client.post(
            f"/api/v1/orders/{order.id}/apply-coupon/",
            {"code": expired_coupon.code},
            format="json",
        )
        self.assertEqual(expired_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("not valid", str(expired_response.data))

    def test_apply_coupon_rejects_ineligible_user_coupon(self):
        other_user = get_user_model().objects.create_user(
            email="other-coupon@example.com",
            password="StrongPass123",
            name="Other Coupon",
        )
        user_only_coupon = Coupon.objects.create(
            code="PRIVATE100",
            discount_type=Coupon.DiscountType.FIXED,
            discount_value=Decimal("100.00"),
            eligible_user=other_user,
            valid_from=timezone.now() - timedelta(days=1),
            valid_until=timezone.now() + timedelta(days=1),
            is_active=True,
        )
        order = Order.objects.create(user=self.user, total_amount=Decimal("1000.00"))
        response = self.client.post(
            f"/api/v1/orders/{order.id}/apply-coupon/",
            {"code": user_only_coupon.code},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("not eligible", str(response.data))


class AdminAnalyticsAPITests(TestCase):
    def setUp(self):
        cache.clear()
        self.admin_user = get_user_model().objects.create_user(
            email="admin-analytics@example.com",
            password="StrongPass123",
            name="Admin Analytics",
            is_staff=True,
        )
        self.regular_user = get_user_model().objects.create_user(
            email="regular-analytics@example.com",
            password="StrongPass123",
            name="Regular Analytics",
        )
        self.other_user = get_user_model().objects.create_user(
            email="other-analytics@example.com",
            password="StrongPass123",
            name="Other Analytics",
        )
        self.client = APIClient()
        self.category = Category.objects.create(name="Analytics Category")
        self.product_a = Product.objects.create(
            category=self.category,
            name="Product A",
            description="A",
            price=Decimal("100.00"),
            sku="AN-A",
            stock_quantity=10,
        )
        self.product_b = Product.objects.create(
            category=self.category,
            name="Product B",
            description="B",
            price=Decimal("200.00"),
            sku="AN-B",
            stock_quantity=10,
        )

    def test_admin_can_access_analytics_metrics(self):
        paid_order = Order.objects.create(
            user=self.regular_user,
            total_amount=Decimal("300.00"),
            payment_status=Order.PaymentStatus.PAID,
            status=Order.Status.CONFIRMED,
        )
        recent_paid_order = Order.objects.create(
            user=self.other_user,
            total_amount=Decimal("500.00"),
            payment_status=Order.PaymentStatus.PAID,
            status=Order.Status.SHIPPED,
        )
        pending_order = Order.objects.create(
            user=self.regular_user,
            total_amount=Decimal("100.00"),
            payment_status=Order.PaymentStatus.PENDING,
            status=Order.Status.PENDING,
        )
        Order.objects.filter(id=paid_order.id).update(created_at=timezone.now() - timedelta(days=3))
        Order.objects.filter(id=recent_paid_order.id).update(created_at=timezone.now() - timedelta(days=1))
        Order.objects.filter(id=pending_order.id).update(created_at=timezone.now() - timedelta(days=2))
        paid_order.refresh_from_db()
        recent_paid_order.refresh_from_db()

        OrderItem.objects.create(order=paid_order, product=self.product_a, quantity=2, price=self.product_a.price)
        OrderItem.objects.create(order=recent_paid_order, product=self.product_a, quantity=1, price=self.product_a.price)
        OrderItem.objects.create(order=recent_paid_order, product=self.product_b, quantity=5, price=self.product_b.price)
        OrderItem.objects.create(order=pending_order, product=self.product_a, quantity=7, price=self.product_a.price)

        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get("/api/v1/admin/analytics/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_orders"], 3)
        self.assertEqual(response.data["total_revenue"], "800.00")
        self.assertEqual(response.data["total_users"], 3)
        self.assertEqual(response.data["top_products"], [
            {"product_id": self.product_b.id, "name": self.product_b.name, "total_sold": 5},
            {"product_id": self.product_a.id, "name": self.product_a.name, "total_sold": 3},
        ])
        self.assertEqual(len(response.data["recent_orders"]), 3)
        self.assertEqual(response.data["recent_orders"][0]["order_id"], recent_paid_order.id)
        self.assertEqual(response.data["recent_orders"][0]["user_email"], self.other_user.email)
        self.assertIn("created_at", response.data["recent_orders"][0])

    def test_non_admin_cannot_access_analytics_metrics(self):
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.get("/api/v1/admin/analytics/")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_analytics_endpoint_is_rate_limited(self):
        cache.clear()
        original_rates = SimpleRateThrottle.THROTTLE_RATES.copy()
        SimpleRateThrottle.THROTTLE_RATES["admin"] = "1/minute"
        try:
            self.client.force_authenticate(user=self.admin_user)
            self.assertEqual(self.client.get("/api/v1/admin/analytics/").status_code, status.HTTP_200_OK)
            self.assertEqual(self.client.get("/api/v1/admin/analytics/").status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        finally:
            SimpleRateThrottle.THROTTLE_RATES = original_rates
            cache.clear()

    def test_admin_analytics_cache_hit_returns_identical_response(self):
        cached_payload = {
            "total_orders": 99,
            "total_revenue": "1234.56",
            "total_users": 7,
            "top_products": [{"product_id": self.product_a.id, "name": self.product_a.name, "total_sold": 12}],
            "recent_orders": [],
        }
        cache.set("admin_analytics_summary", cached_payload, timeout=120)
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get("/api/v1/admin/analytics/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, cached_payload)

    def test_admin_analytics_cache_miss_populates_cache_with_ttl(self):
        self.client.force_authenticate(user=self.admin_user)
        cache.delete("admin_analytics_summary")
        response = self.client.get("/api/v1/admin/analytics/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(cache.get("admin_analytics_summary"))
        if hasattr(cache, "_expire_info"):
            remaining_ttl = cache._expire_info[cache.make_key("admin_analytics_summary")] - time.time()
            self.assertGreater(remaining_ttl, 0)
            self.assertLessEqual(remaining_ttl, 120)


class AdminOrderManagementAPITests(TestCase):
    def setUp(self):
        self.admin_user = get_user_model().objects.create_user(
            email="admin@example.com",
            password="StrongPass123",
            name="Admin User",
            is_staff=True,
        )
        self.customer_user = get_user_model().objects.create_user(
            email="customer@example.com",
            password="StrongPass123",
            name="Customer User",
        )
        self.client = APIClient()
        self.category = Category.objects.create(name="Devices")
        self.product = Product.objects.create(
            category=self.category,
            name="Keyboard",
            description="Mechanical keyboard",
            price=Decimal("3500.00"),
            sku="KBD-001",
            stock_quantity=15,
        )
        self.order = Order.objects.create(
            user=self.customer_user,
            total_amount=Decimal("7000.00"),
            payment_status=Order.PaymentStatus.PAID,
        )
        OrderItem.objects.create(order=self.order, product=self.product, quantity=2, price=self.product.price)
        ShippingAddress.objects.create(
            order=self.order,
            full_name="Customer User",
            phone_number="9999999999",
            address_line_1="12 Main Street",
            city="Bengaluru",
            state="Karnataka",
            postal_code="560001",
            country="India",
        )

    def test_non_admin_cannot_access_admin_order_endpoints(self):
        self.client.force_authenticate(user=self.customer_user)

        response = self.client.get("/admin/orders/")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_list_and_filter_orders(self):
        second_user = get_user_model().objects.create_user(
            email="another@example.com",
            password="StrongPass123",
            name="Another User",
        )
        Order.objects.create(
            user=second_user,
            total_amount=Decimal("1100.00"),
            status=Order.Status.CANCELLED,
        )
        self.client.force_authenticate(user=self.admin_user)

        by_status = self.client.get("/admin/orders/", {"status": "cancelled"})
        by_search = self.client.get("/admin/orders/", {"search": "customer@example.com"})

        self.assertEqual(by_status.status_code, status.HTTP_200_OK)
        self.assertEqual(by_status.data["count"], 1)
        self.assertEqual(by_status.data["results"][0]["status"], Order.Status.CANCELLED)
        self.assertEqual(by_search.status_code, status.HTTP_200_OK)
        self.assertEqual(by_search.data["count"], 1)
        self.assertEqual(by_search.data["results"][0]["id"], self.order.id)

    def test_admin_can_view_order_detail(self):
        self.client.force_authenticate(user=self.admin_user)

        response = self.client.get(f"/admin/orders/{self.order.id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user_email"], self.customer_user.email)
        self.assertEqual(len(response.data["items"]), 1)
        self.assertEqual(response.data["shipping_address"]["city"], "Bengaluru")
        self.assertIn("timeline", response.data)

    def test_admin_status_update_creates_order_event(self):
        self.client.force_authenticate(user=self.admin_user)

        response = self.client.post(
            f"/admin/orders/{self.order.id}/status/",
            {"status": "processing", "payment_status": Order.PaymentStatus.PAID},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.CONFIRMED)
        self.assertEqual(self.order.payment_status, Order.PaymentStatus.PAID)
        event = OrderEvent.objects.get(order=self.order)
        self.assertEqual(event.previous_status, Order.Status.PENDING)
        self.assertEqual(event.new_status, Order.Status.CONFIRMED)
        self.assertEqual(event.changed_by, self.admin_user)

    @patch("adminpanel.views.send_order_email_task.delay")
    def test_admin_ship_endpoint_sets_tracking_and_creates_shipping_event(self, mock_delay):
        self.client.force_authenticate(user=self.admin_user)
        self.order.status = Order.Status.CONFIRMED
        self.order.save(update_fields=["status", "updated_at"])

        response = self.client.post(
            f"/admin/orders/{self.order.id}/ship/",
            {"shipping_provider": "BlueDart", "location": "Bengaluru Hub"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.SHIPPED)
        self.assertEqual(self.order.shipping_provider, "BlueDart")
        self.assertTrue(self.order.tracking_id)
        self.assertIsNotNone(self.order.shipped_at)
        shipping_event = ShippingEvent.objects.get(order=self.order)
        self.assertEqual(shipping_event.event_type, ShippingEvent.EventType.CREATED)
        self.assertEqual(shipping_event.location, "Bengaluru Hub")
        mock_delay.assert_called_once_with("order_shipped", self.order.id)

    @patch("adminpanel.views.send_order_email_task.delay")
    def test_admin_deliver_endpoint_marks_order_delivered_and_creates_event(self, mock_delay):
        self.client.force_authenticate(user=self.admin_user)
        self.order.status = Order.Status.SHIPPED
        self.order.shipped_at = timezone.now() - timedelta(hours=3)
        self.order.tracking_id = "TRK-EXISTING"
        self.order.shipping_provider = "BlueDart"
        self.order.save(update_fields=["status", "shipped_at", "tracking_id", "shipping_provider", "updated_at"])

        response = self.client.post(
            f"/admin/orders/{self.order.id}/deliver/",
            {"location": "Customer Address"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.DELIVERED)
        self.assertIsNotNone(self.order.delivered_at)
        shipping_event = ShippingEvent.objects.get(order=self.order, event_type=ShippingEvent.EventType.DELIVERED)
        self.assertEqual(shipping_event.location, "Customer Address")
        mock_delay.assert_called_once_with("order_delivered", self.order.id)

    @patch("adminpanel.views.send_order_email_task.delay")
    def test_admin_status_update_triggers_shipped_and_delivered_emails(self, mock_delay):
        self.client.force_authenticate(user=self.admin_user)

        shipped_response = self.client.post(
            f"/admin/orders/{self.order.id}/status/",
            {"status": Order.Status.SHIPPED, "payment_status": Order.PaymentStatus.PAID},
            format="json",
        )
        delivered_response = self.client.post(
            f"/admin/orders/{self.order.id}/status/",
            {"status": Order.Status.DELIVERED, "payment_status": Order.PaymentStatus.PAID},
            format="json",
        )

        self.assertEqual(shipped_response.status_code, status.HTTP_200_OK)
        self.assertEqual(delivered_response.status_code, status.HTTP_200_OK)
        self.assertEqual(mock_delay.call_count, 2)
        mock_delay.assert_any_call("order_shipped", self.order.id)
        mock_delay.assert_any_call("order_delivered", self.order.id)


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="no-reply@example.com",
    SUPPORT_EMAIL="support@example.com",
)
class OrderNotificationServiceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="notify@example.com",
            password="StrongPass123",
            name="Notify User",
        )
        self.category = Category.objects.create(name="NotifyCategory")
        self.product = Product.objects.create(
            category=self.category,
            name="Notify Product",
            description="Notification test product",
            price=Decimal("2500.00"),
            sku="NTF-001",
            stock_quantity=50,
        )
        self.order = Order.objects.create(
            user=self.user,
            total_amount=Decimal("5000.00"),
            status=Order.Status.CONFIRMED,
            payment_status=Order.PaymentStatus.PAID,
        )
        OrderItem.objects.create(order=self.order, product=self.product, quantity=2, price=self.product.price)

    def test_send_order_email_sends_once_and_persists_sent_event(self):
        first = send_order_email("payment_success", self.order)
        second = send_order_email("payment_success", self.order)

        self.assertTrue(first)
        self.assertFalse(second)
        self.assertEqual(len(mail.outbox), 1)
        sent_event = EmailEvent.objects.get(order=self.order, email_type=EmailEvent.EmailType.PAYMENT_SUCCESS)
        self.assertEqual(sent_event.status, EmailEvent.Status.SENT)
        self.assertIsNotNone(sent_event.sent_at)
        self.assertIn(f"Order ID: {self.order.id}", mail.outbox[0].body)
        self.assertIn("Notify Product", mail.outbox[0].body)
        self.assertIn("support@example.com", mail.outbox[0].body)


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="no-reply@example.com",
    SUPPORT_EMAIL="support@example.com",
    FRONTEND_APP_URL="http://localhost:3000",
)
class AbandonedCartRecoveryTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="cart-user@example.com",
            password="StrongPass123",
            name="Cart User",
        )
        self.category = Category.objects.create(name="Cart Category")
        self.product = Product.objects.create(
            category=self.category,
            name="Cart Product",
            description="Cart reminder test product",
            price=Decimal("1200.00"),
            sku="CRT-001",
            stock_quantity=50,
        )
        self.cart = Cart.objects.create(user=self.user)
        self.cart.items.create(product=self.product, quantity=2)

    def _set_cart_inactive_for_hours(self, hours):
        stale_time = timezone.now() - timedelta(hours=hours)
        Cart.objects.filter(pk=self.cart.pk).update(updated_at=stale_time)
        self.cart.refresh_from_db()

    def test_send_abandoned_cart_reminders_sends_for_stale_cart_with_products(self):
        self._set_cart_inactive_for_hours(3)

        sent_count = send_abandoned_cart_reminders()

        self.assertEqual(sent_count, 1)
        self.assertEqual(len(mail.outbox), 1)
        email_body = mail.outbox[0].body
        self.assertIn("Cart Product x 2", email_body)
        self.assertIn("http://localhost:3000/cart", email_body)
        self.assertIn("support@example.com", email_body)
        self.cart.refresh_from_db()
        self.assertIsNotNone(self.cart.abandoned_cart_reminder_sent_at)

    def test_send_abandoned_cart_reminders_skips_recent_cart(self):
        self._set_cart_inactive_for_hours(1)

        sent_count = send_abandoned_cart_reminders()

        self.assertEqual(sent_count, 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_send_abandoned_cart_reminders_does_not_repeat_without_cart_update(self):
        self._set_cart_inactive_for_hours(3)

        first_sent = send_abandoned_cart_reminders()
        second_sent = send_abandoned_cart_reminders()

        self.assertEqual(first_sent, 1)
        self.assertEqual(second_sent, 0)
        self.assertEqual(len(mail.outbox), 1)

    def test_cart_updated_at_is_touched_when_cart_item_changes(self):
        original_updated_at = self.cart.updated_at
        cart_item = self.cart.items.get(product=self.product)
        cart_item.quantity = 3
        cart_item.save(update_fields=["quantity"])
        self.cart.refresh_from_db()

        self.assertGreater(self.cart.updated_at, original_updated_at)

    def test_management_command_sends_reminder_emails(self):
        self._set_cart_inactive_for_hours(3)

        call_command("send_abandoned_cart_reminders")

        self.assertEqual(len(mail.outbox), 1)


class ServerCartApiTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="server-cart@example.com",
            password="StrongPass123",
            name="Server Cart User",
        )
        self.category = Category.objects.create(name="Components")
        self.product = Product.objects.create(
            category=self.category,
            name="Arduino Kit",
            description="Starter kit",
            price=Decimal("1499.00"),
            sku="ARD-001",
            stock_quantity=25,
            is_refurbished=False,
            condition_grade="A",
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_active_cart_endpoint_creates_empty_cart(self):
        response = self.client.get("/api/v1/orders/carts/active/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["is_active"])
        self.assertEqual(response.data["items"], [])
        self.assertEqual(response.data["item_count"], 0)
        self.assertEqual(response.data["subtotal"], "0.00")
        self.assertEqual(Cart.objects.filter(user=self.user, is_active=True).count(), 1)

    def test_cart_item_list_returns_nested_product(self):
        cart = Cart.objects.create(user=self.user, is_active=True)
        self.client.post(
            "/api/v1/orders/cart-items/",
            {"cart": cart.id, "product": self.product.id, "quantity": 2},
            format="json",
        )

        response = self.client.get("/api/v1/orders/cart-items/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["product"]["id"], self.product.id)
        self.assertEqual(response.data[0]["product"]["name"], "Arduino Kit")
        self.assertEqual(response.data[0]["quantity"], 2)
        self.assertEqual(response.data[0]["line_total"], "2998.00")

    def test_add_same_product_merges_quantity(self):
        cart = Cart.objects.create(user=self.user, is_active=True)
        self.client.post(
            "/api/v1/orders/cart-items/",
            {"cart": cart.id, "product": self.product.id, "quantity": 1},
            format="json",
        )
        self.client.post(
            "/api/v1/orders/cart-items/",
            {"cart": cart.id, "product": self.product.id, "quantity": 3},
            format="json",
        )

        cart_item = cart.items.get(product=self.product)
        self.assertEqual(cart_item.quantity, 4)

    def test_clear_active_cart_removes_items(self):
        cart = Cart.objects.create(user=self.user, is_active=True)
        cart.items.create(product=self.product, quantity=1)

        response = self.client.delete("/api/v1/orders/carts/active/clear/")

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(cart.items.count(), 0)
        self.assertTrue(Cart.objects.filter(pk=cart.pk, is_active=True).exists())


@override_settings(
    RAZORPAY_KEY_ID="rzp_test_key",
    RAZORPAY_KEY_SECRET="rzp_test_secret",
)
class CheckoutLifecycleTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="checkout@example.com",
            password="StrongPass123",
            name="Checkout User",
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.category = Category.objects.create(name="Checkout Category")
        self.product = Product.objects.create(
            category=self.category,
            name="Checkout Product",
            description="Checkout ready",
            price=Decimal("999.00"),
            sku="CHK-001",
            stock_quantity=5,
        )
        self.cart = Cart.objects.create(user=self.user, is_active=True)
        self.cart.items.create(product=self.product, quantity=2)

    @patch("orders.views.create_razorpay_order")
    def test_checkout_from_cart_creates_reservation_and_payment(self, mock_create):
        mock_create.return_value = {
            "id": "order_checkout_1",
            "amount": 199800,
            "currency": "INR",
            "status": "created",
        }

        response = self.client.post(
            "/api/v1/orders/checkout-from-cart/",
            {},
            format="json",
            HTTP_IDEMPOTENCY_KEY="checkout-1",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        order_id = response.data["order"]["id"]
        order = Order.objects.get(id=order_id)
        self.assertEqual(order.status, Order.Status.PENDING_PAYMENT)
        self.assertEqual(order.payment_status, Order.PaymentStatus.PENDING_PAYMENT)
        self.assertIsNotNone(order.reservation_expires_at)
        self.assertEqual(
            InventoryReservation.objects.filter(
                order=order,
                status=InventoryReservation.Status.ACTIVE,
            ).count(),
            1,
        )
        payment = Payment.objects.get(order=order)
        self.assertEqual(payment.razorpay_order_id, "order_checkout_1")
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 5)

        repeat = self.client.post(
            "/api/v1/orders/checkout-from-cart/",
            {},
            format="json",
            HTTP_IDEMPOTENCY_KEY="checkout-1",
        )

        self.assertEqual(repeat.status_code, status.HTTP_200_OK)
        self.assertEqual(repeat.data["order"]["id"], order.id)

    @patch("orders.views.create_razorpay_order")
    def test_checkout_respects_inventory_contention(self, mock_create):
        mock_create.side_effect = [
            {"id": "order_checkout_user1", "amount": 99900, "currency": "INR", "status": "created"},
        ]
        other_user = get_user_model().objects.create_user(
            email="checkout2@example.com",
            password="StrongPass123",
            name="Checkout User 2",
        )
        other_client = APIClient()
        other_client.force_authenticate(user=other_user)
        other_cart = Cart.objects.create(user=other_user, is_active=True)
        other_cart.items.create(product=self.product, quantity=4)

        first = self.client.post(
            "/api/v1/orders/checkout-from-cart/",
            {},
            format="json",
            HTTP_IDEMPOTENCY_KEY="checkout-first",
        )
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)

        second = other_client.post(
            "/api/v1/orders/checkout-from-cart/",
            {},
            format="json",
            HTTP_IDEMPOTENCY_KEY="checkout-second",
        )

        self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            InventoryReservation.objects.filter(order__user=other_user).count(),
            0,
        )


class ReservationExpirationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="reserve@example.com",
            password="StrongPass123",
            name="Reserve User",
        )
        self.category = Category.objects.create(name="Reservation Category")
        self.product = Product.objects.create(
            category=self.category,
            name="Reservation Product",
            description="Reserved",
            price=Decimal("499.00"),
            sku="RSV-001",
            stock_quantity=3,
        )
        self.order = Order.objects.create(
            user=self.user,
            total_amount=Decimal("998.00"),
        )
        OrderItem.objects.create(order=self.order, product=self.product, quantity=2, price=self.product.price)
        reserve_order_inventory(self.order)

    def test_expire_stale_reservations_cancels_order(self):
        past = timezone.now() - timedelta(minutes=20)
        Order.objects.filter(id=self.order.id).update(reservation_expires_at=past)
        InventoryReservation.objects.filter(order=self.order).update(expires_at=past)

        released_count = expire_stale_reservations(now=timezone.now())

        self.assertEqual(released_count, 1)
        self.order.refresh_from_db()
        reservation = InventoryReservation.objects.get(order=self.order)
        self.assertEqual(self.order.payment_status, Order.PaymentStatus.CANCELLED)
        self.assertEqual(self.order.status, Order.Status.CANCELLED)
        self.assertEqual(reservation.status, InventoryReservation.Status.RELEASED)
        self.assertIsNotNone(self.order.reservation_released_at)

    @override_settings(
        CELERY_TASK_ALWAYS_EAGER=True,
        CELERY_TASK_EAGER_PROPAGATES=True,
    )
    def test_cleanup_task_releases_stale_pending_orders(self):
        stale_time = timezone.now() - timedelta(hours=3)
        Order.objects.filter(id=self.order.id).update(created_at=stale_time)

        cleanup_stale_checkout_sessions_task.delay()

        self.order.refresh_from_db()
        reservation = InventoryReservation.objects.get(order=self.order)
        self.assertEqual(self.order.payment_status, Order.PaymentStatus.CANCELLED)
        self.assertEqual(self.order.status, Order.Status.CANCELLED)
        self.assertEqual(reservation.status, InventoryReservation.Status.RELEASED)
