import hashlib
import hmac
import json
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework.throttling import SimpleRateThrottle

from orders.inventory import reserve_order_inventory
from orders.models import Coupon, InventoryAuditLog, InventoryReservation, Order, OrderItem
from products.models import Category, Product
from users.models import Referral

from .models import Payment, PaymentEvent, PaymentWebhookEvent


class MockHTTPResponse:
    def __init__(self, payload):
        self.payload = payload

    def read(self):
        return json.dumps(self.payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


@override_settings(
    RAZORPAY_KEY_ID="rzp_test_key",
    RAZORPAY_KEY_SECRET="rzp_test_secret",
    RAZORPAY_WEBHOOK_SECRET="rzp_webhook_secret",
    RAZORPAY_API_BASE_URL="https://api.razorpay.com/v1",
)
class PaymentAPITests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="payer@example.com",
            password="StrongPass123",
            name="Payer",
        )
        self.order = Order.objects.create(user=self.user, total_amount=Decimal("999.00"))
        category = Category.objects.create(name="Payments")
        self.product = Product.objects.create(
            category=category,
            name="Keyboard",
            description="Mechanical keyboard",
            price=Decimal("999.00"),
            sku="PAY-001",
            stock_quantity=5,
        )
        OrderItem.objects.create(order=self.order, product=self.product, quantity=2, price=Decimal("999.00"))
        reserve_order_inventory(self.order)
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    @patch("payments.services.urlopen")
    def test_create_order_with_idempotency(self, mock_urlopen):
        mock_urlopen.return_value = MockHTTPResponse(
            {"id": "order_123", "amount": 99900, "currency": "INR", "status": "created"}
        )

        response = self.client.post(
            "/api/v1/payments/create-order/",
            {"order_id": self.order.id, "idempotency_key": "idem-1"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Payment.objects.count(), 1)

        second = self.client.post(
            "/api/v1/payments/create-order/",
            {"order_id": self.order.id, "idempotency_key": "idem-1"},
            format="json",
        )
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(Payment.objects.count(), 1)
        self.assertEqual(mock_urlopen.call_count, 1)

    @patch("payments.services.urlopen")
    def test_payment_create_order_endpoint_is_rate_limited(self, mock_urlopen):
        cache.clear()
        original_rates = SimpleRateThrottle.THROTTLE_RATES.copy()
        SimpleRateThrottle.THROTTLE_RATES["payments"] = "2/minute"
        mock_urlopen.side_effect = [
            MockHTTPResponse({"id": "order_rate_limited_1", "amount": 99900, "currency": "INR", "status": "created"}),
            MockHTTPResponse({"id": "order_rate_limited_2", "amount": 99900, "currency": "INR", "status": "created"}),
        ]
        try:
            self.assertEqual(
                self.client.post(
                    "/api/v1/payments/create-order/",
                    {"order_id": self.order.id, "idempotency_key": "rate-idem-1"},
                    format="json",
                ).status_code,
                status.HTTP_201_CREATED,
            )
            self.assertEqual(
                self.client.post(
                    "/api/v1/payments/create-order/",
                    {"order_id": self.order.id, "idempotency_key": "rate-idem-2"},
                    format="json",
                ).status_code,
                status.HTTP_201_CREATED,
            )
            self.assertEqual(
                self.client.post(
                    "/api/v1/payments/create-order/",
                    {"order_id": self.order.id, "idempotency_key": "rate-idem-3"},
                    format="json",
                ).status_code,
                status.HTTP_429_TOO_MANY_REQUESTS,
            )
        finally:
            SimpleRateThrottle.THROTTLE_RATES = original_rates
            cache.clear()

    @patch("payments.views.send_order_email_task.delay")
    def test_payment_verification_and_duplicate_prevention(self, mock_delay):
        payment = Payment.objects.create(
            order=self.order,
            idempotency_key="idem-2",
            razorpay_order_id="order_ver_1",
            amount=99900,
        )
        signature = hmac.new(
            b"rzp_test_secret",
            msg=b"order_ver_1|pay_1",
            digestmod=hashlib.sha256,
        ).hexdigest()

        response = self.client.post(
            "/api/v1/payments/verify/",
            {
                "razorpay_order_id": "order_ver_1",
                "razorpay_payment_id": "pay_1",
                "razorpay_signature": signature,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payment.refresh_from_db()
        self.order.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.CAPTURED)
        self.assertEqual(self.order.payment_status, Order.PaymentStatus.PAID)
        self.assertEqual(self.order.status, Order.Status.PAID)
        self.assertTrue(self.order.stock_deducted)
        self.assertEqual(self.product.stock_quantity, 3)
        self.assertEqual(payment.events.filter(event_type=PaymentEvent.EventType.PAYMENT_SUCCESS).count(), 1)
        mock_delay.assert_called_once_with("payment_success", self.order.id)
        verified_at = payment.verified_at
        order_updated_at = self.order.updated_at

        already_verified = self.client.post(
            "/api/v1/payments/verify/",
            {
                "razorpay_order_id": "order_ver_1",
                "razorpay_payment_id": "pay_1",
                "razorpay_signature": signature,
            },
            format="json",
        )
        self.assertEqual(already_verified.status_code, status.HTTP_200_OK)
        self.assertEqual(already_verified.data["detail"], "Payment already verified.")
        payment.refresh_from_db()
        self.order.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.CAPTURED)
        self.assertEqual(payment.verified_at, verified_at)
        self.assertEqual(self.order.payment_status, Order.PaymentStatus.PAID)
        self.assertEqual(self.order.status, Order.Status.PAID)
        self.assertEqual(self.order.updated_at, order_updated_at)
        self.assertEqual(self.product.stock_quantity, 3)
        self.assertEqual(payment.events.filter(event_type=PaymentEvent.EventType.REPLAY).count(), 1)
        self.assertEqual(mock_delay.call_count, 1)

        another_order = Order.objects.create(user=self.user, total_amount=Decimal("100.00"))
        Payment.objects.create(
            order=another_order,
            idempotency_key="idem-3",
            razorpay_order_id="order_ver_2",
            amount=10000,
        )
        duplicate = self.client.post(
            "/api/v1/payments/verify/",
            {
                "razorpay_order_id": "order_ver_2",
                "razorpay_payment_id": "pay_1",
                "razorpay_signature": hmac.new(
                    b"rzp_test_secret",
                    msg=b"order_ver_2|pay_1",
                    digestmod=hashlib.sha256,
                ).hexdigest(),
            },
            format="json",
        )
        self.assertEqual(duplicate.status_code, status.HTTP_409_CONFLICT)
        duplicate_payment = Payment.objects.get(razorpay_order_id="order_ver_2")
        self.assertEqual(duplicate_payment.events.filter(event_type=PaymentEvent.EventType.DUPLICATE).count(), 1)

    def test_payment_verification_finalizes_reservation_and_audit_log(self):
        payment = Payment.objects.create(
            order=self.order,
            idempotency_key="idem-finalize",
            razorpay_order_id="order_finalize_1",
            amount=99900,
        )
        signature = hmac.new(
            b"rzp_test_secret",
            msg=b"order_finalize_1|pay_finalize_1",
            digestmod=hashlib.sha256,
        ).hexdigest()

        response = self.client.post(
            "/api/v1/payments/verify/",
            {
                "razorpay_order_id": "order_finalize_1",
                "razorpay_payment_id": "pay_finalize_1",
                "razorpay_signature": signature,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        reservation = InventoryReservation.objects.get(order=self.order)
        self.assertEqual(reservation.status, InventoryReservation.Status.FINALIZED)
        self.assertIsNotNone(reservation.finalized_at)
        audit = InventoryAuditLog.objects.filter(
            order=self.order,
            reason=InventoryAuditLog.Reason.FINALIZE,
        ).first()
        self.assertIsNotNone(audit)

    def test_first_referred_paid_order_issues_reward_coupon_once(self):
        referrer = get_user_model().objects.create_user(
            email="referrer@example.com",
            password="StrongPass123",
            name="Referrer",
        )
        referred_user = get_user_model().objects.create_user(
            email="referred-payer@example.com",
            password="StrongPass123",
            name="Referred Payer",
        )
        Referral.objects.create(referrer=referrer, referred_user=referred_user)
        referred_order = Order.objects.create(user=referred_user, total_amount=Decimal("500.00"))
        OrderItem.objects.create(order=referred_order, product=self.product, quantity=1, price=Decimal("500.00"))
        reserve_order_inventory(referred_order)
        payment = Payment.objects.create(
            order=referred_order,
            idempotency_key="idem-referred",
            razorpay_order_id="order_ref_1",
            amount=50000,
        )
        signature = hmac.new(
            b"rzp_test_secret",
            msg=b"order_ref_1|pay_ref_1",
            digestmod=hashlib.sha256,
        ).hexdigest()
        self.client.force_authenticate(referred_user)

        response = self.client.post(
            "/api/v1/payments/verify/",
            {
                "razorpay_order_id": "order_ref_1",
                "razorpay_payment_id": "pay_ref_1",
                "razorpay_signature": signature,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        referral = Referral.objects.get(referred_user=referred_user)
        self.assertTrue(referral.reward_issued)
        reward_coupons = Coupon.objects.filter(eligible_user=referrer, discount_value=Decimal("100.00"))
        self.assertEqual(reward_coupons.count(), 1)
        reward_coupon = reward_coupons.first()
        self.assertEqual(reward_coupon.discount_type, Coupon.DiscountType.FIXED)
        self.assertEqual(reward_coupon.max_uses, 1)
        self.assertEqual(reward_coupon.per_user_limit, 1)

    def test_payment_verification_fails_when_stock_is_insufficient(self):
        low_stock_order = Order.objects.create(user=self.user, total_amount=Decimal("999.00"))
        OrderItem.objects.create(order=low_stock_order, product=self.product, quantity=2, price=Decimal("999.00"))
        reserve_order_inventory(low_stock_order)
        self.product.stock_quantity = 1
        self.product.save(update_fields=["stock_quantity", "updated_at"])
        payment = Payment.objects.create(
            order=low_stock_order,
            idempotency_key="idem-stock-low",
            razorpay_order_id="order_stock_low",
            amount=99900,
        )
        signature = hmac.new(
            b"rzp_test_secret",
            msg=b"order_stock_low|pay_stock_low",
            digestmod=hashlib.sha256,
        ).hexdigest()

        response = self.client.post(
            "/api/v1/payments/verify/",
            {
                "razorpay_order_id": "order_stock_low",
                "razorpay_payment_id": "pay_stock_low",
                "razorpay_signature": signature,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        payment.refresh_from_db()
        low_stock_order.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.CREATED)
        self.assertEqual(low_stock_order.payment_status, Order.PaymentStatus.PENDING_PAYMENT)
        self.assertEqual(low_stock_order.status, Order.Status.PENDING_PAYMENT)
        self.assertFalse(low_stock_order.stock_deducted)
        self.assertEqual(self.product.stock_quantity, 1)
        self.assertEqual(
            InventoryReservation.objects.filter(
                order=low_stock_order,
                status=InventoryReservation.Status.ACTIVE,
            ).count(),
            1,
        )

    def test_payment_verification_sets_paid_status(self):
        self.order.status = Order.Status.CONFIRMED
        self.order.save(update_fields=["status", "updated_at"])
        payment = Payment.objects.create(
            order=self.order,
            idempotency_key="idem-confirmed",
            razorpay_order_id="order_confirmed_1",
            amount=99900,
        )
        signature = hmac.new(
            b"rzp_test_secret",
            msg=b"order_confirmed_1|pay_confirmed_1",
            digestmod=hashlib.sha256,
        ).hexdigest()

        response = self.client.post(
            "/api/v1/payments/verify/",
            {
                "razorpay_order_id": "order_confirmed_1",
                "razorpay_payment_id": "pay_confirmed_1",
                "razorpay_signature": signature,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payment.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.CAPTURED)
        self.assertEqual(self.order.status, Order.Status.PAID)
        self.assertEqual(self.order.payment_status, Order.PaymentStatus.PAID)

    def test_webhook_idempotency(self):
        payment = Payment.objects.create(
            order=self.order,
            idempotency_key="idem-4",
            razorpay_order_id="order_webhook_1",
            amount=99900,
        )
        payload = {
            "event": "payment.failed",
            "payload": {"payment": {"entity": {"id": "pay_web_1", "order_id": "order_webhook_1"}}},
        }
        body = json.dumps(payload).encode()
        signature = hmac.new(b"rzp_webhook_secret", msg=body, digestmod=hashlib.sha256).hexdigest()

        response = self.client.post(
            "/api/v1/payments/webhook/",
            data=body,
            content_type="application/json",
            HTTP_X_RAZORPAY_SIGNATURE=signature,
            HTTP_X_RAZORPAY_EVENT_ID="evt_1",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(PaymentWebhookEvent.objects.count(), 1)
        payment.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.FAILED)
        self.assertEqual(self.order.payment_status, Order.PaymentStatus.CANCELLED)
        self.assertEqual(self.order.status, Order.Status.CANCELLED)
        self.assertEqual(
            InventoryReservation.objects.filter(
                order=self.order,
                status=InventoryReservation.Status.RELEASED,
            ).count(),
            1,
        )

        duplicate = self.client.post(
            "/api/v1/payments/webhook/",
            data=body,
            content_type="application/json",
            HTTP_X_RAZORPAY_SIGNATURE=signature,
            HTTP_X_RAZORPAY_EVENT_ID="evt_1",
        )
        self.assertEqual(duplicate.status_code, status.HTTP_200_OK)
        self.assertEqual(PaymentWebhookEvent.objects.count(), 1)

    def test_webhook_endpoint_is_rate_limited(self):
        cache.clear()
        original_rates = SimpleRateThrottle.THROTTLE_RATES.copy()
        SimpleRateThrottle.THROTTLE_RATES["payments_webhook"] = "2/minute"
        payload = {
            "event": "payment.failed",
            "payload": {"payment": {"entity": {"id": "pay_web_rate", "order_id": "order_webhook_rate"}}},
        }
        body = json.dumps(payload).encode()
        signature = hmac.new(b"rzp_webhook_secret", msg=body, digestmod=hashlib.sha256).hexdigest()
        anonymous_client = APIClient()
        try:
            self.assertEqual(
                anonymous_client.post(
                    "/api/v1/payments/webhook/",
                    data=body,
                    content_type="application/json",
                    HTTP_X_RAZORPAY_SIGNATURE=signature,
                    HTTP_X_RAZORPAY_EVENT_ID="evt_rate_1",
                ).status_code,
                status.HTTP_200_OK,
            )
            self.assertEqual(
                anonymous_client.post(
                    "/api/v1/payments/webhook/",
                    data=body,
                    content_type="application/json",
                    HTTP_X_RAZORPAY_SIGNATURE=signature,
                    HTTP_X_RAZORPAY_EVENT_ID="evt_rate_2",
                ).status_code,
                status.HTTP_200_OK,
            )
            self.assertEqual(
                anonymous_client.post(
                    "/api/v1/payments/webhook/",
                    data=body,
                    content_type="application/json",
                    HTTP_X_RAZORPAY_SIGNATURE=signature,
                    HTTP_X_RAZORPAY_EVENT_ID="evt_rate_3",
                ).status_code,
                status.HTTP_429_TOO_MANY_REQUESTS,
            )
        finally:
            SimpleRateThrottle.THROTTLE_RATES = original_rates
            cache.clear()

    def test_webhook_does_not_downgrade_paid_order(self):
        payment = Payment.objects.create(
            order=self.order,
            idempotency_key="idem-5",
            razorpay_order_id="order_webhook_2",
            amount=99900,
        )
        self.order.payment_status = Order.PaymentStatus.PAID
        self.order.save(update_fields=["payment_status", "updated_at"])

        payload = {
            "event": "payment.failed",
            "payload": {"payment": {"entity": {"id": "pay_web_2", "order_id": "order_webhook_2"}}},
        }
        body = json.dumps(payload).encode()
        signature = hmac.new(b"rzp_webhook_secret", msg=body, digestmod=hashlib.sha256).hexdigest()

        response = self.client.post(
            "/api/v1/payments/webhook/",
            data=body,
            content_type="application/json",
            HTTP_X_RAZORPAY_SIGNATURE=signature,
            HTTP_X_RAZORPAY_EVENT_ID="evt_2",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payment.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.CREATED)
        self.assertEqual(self.order.payment_status, Order.PaymentStatus.PAID)

    def test_webhook_does_not_change_failed_order_to_paid(self):
        payment = Payment.objects.create(
            order=self.order,
            idempotency_key="idem-6",
            razorpay_order_id="order_webhook_3",
            amount=99900,
            status=Payment.Status.FAILED,
        )
        self.order.payment_status = Order.PaymentStatus.FAILED
        self.order.status = Order.Status.FAILED
        self.order.save(update_fields=["payment_status", "status", "updated_at"])

        payload = {
            "event": "payment.captured",
            "payload": {"payment": {"entity": {"id": "pay_web_3", "order_id": "order_webhook_3"}}},
        }
        body = json.dumps(payload).encode()
        signature = hmac.new(b"rzp_webhook_secret", msg=body, digestmod=hashlib.sha256).hexdigest()

        response = self.client.post(
            "/api/v1/payments/webhook/",
            data=body,
            content_type="application/json",
            HTTP_X_RAZORPAY_SIGNATURE=signature,
            HTTP_X_RAZORPAY_EVENT_ID="evt_3",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payment.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.FAILED)
        self.assertEqual(self.order.payment_status, Order.PaymentStatus.FAILED)

    @patch("payments.views.send_order_email_task.delay")
    def test_webhook_captured_deducts_stock_once(self, mock_delay):
        payment = Payment.objects.create(
            order=self.order,
            idempotency_key="idem-captured",
            razorpay_order_id="order_webhook_4",
            amount=99900,
        )
        payload = {
            "event": "payment.captured",
            "payload": {"payment": {"entity": {"id": "pay_web_4", "order_id": "order_webhook_4"}}},
        }
        body = json.dumps(payload).encode()
        signature = hmac.new(b"rzp_webhook_secret", msg=body, digestmod=hashlib.sha256).hexdigest()

        response = self.client.post(
            "/api/v1/payments/webhook/",
            data=body,
            content_type="application/json",
            HTTP_X_RAZORPAY_SIGNATURE=signature,
            HTTP_X_RAZORPAY_EVENT_ID="evt_4",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payment.refresh_from_db()
        self.order.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.CAPTURED)
        self.assertEqual(self.order.payment_status, Order.PaymentStatus.PAID)
        self.assertEqual(self.order.status, Order.Status.PAID)
        self.assertTrue(self.order.stock_deducted)
        self.assertEqual(self.product.stock_quantity, 3)
        mock_delay.assert_called_once_with("payment_success", self.order.id)

    @patch("payments.views.send_order_email_task.delay")
    def test_webhook_replay_does_not_double_deduct(self, mock_delay):
        payment = Payment.objects.create(
            order=self.order,
            idempotency_key="idem-replay",
            razorpay_order_id="order_webhook_replay",
            amount=99900,
        )
        payload = {
            "event": "payment.captured",
            "payload": {"payment": {"entity": {"id": "pay_web_replay", "order_id": "order_webhook_replay"}}},
        }
        body = json.dumps(payload).encode()
        signature = hmac.new(b"rzp_webhook_secret", msg=body, digestmod=hashlib.sha256).hexdigest()

        first = self.client.post(
            "/api/v1/payments/webhook/",
            data=body,
            content_type="application/json",
            HTTP_X_RAZORPAY_SIGNATURE=signature,
            HTTP_X_RAZORPAY_EVENT_ID="evt_replay_1",
        )
        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 3)

        second = self.client.post(
            "/api/v1/payments/webhook/",
            data=body,
            content_type="application/json",
            HTTP_X_RAZORPAY_SIGNATURE=signature,
            HTTP_X_RAZORPAY_EVENT_ID="evt_replay_1",
        )
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 3)
        self.assertEqual(PaymentWebhookEvent.objects.count(), 1)
        self.assertEqual(mock_delay.call_count, 1)

    @patch("payments.views.send_order_email_task.delay")
    def test_refund_order_is_idempotent(self, mock_delay):
        payment = Payment.objects.create(
            order=self.order,
            idempotency_key="idem-refund",
            razorpay_order_id="order_refund_1",
            amount=99900,
            status=Payment.Status.CAPTURED,
        )
        self.order.payment_status = Order.PaymentStatus.PAID
        self.order.status = Order.Status.PAID
        self.order.save(update_fields=["payment_status", "status", "updated_at"])

        response = self.client.post(
            "/api/v1/payments/refund/",
            {"order_id": self.order.id},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payment.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.REFUNDED)
        self.assertEqual(self.order.payment_status, Order.PaymentStatus.REFUNDED)
        self.assertEqual(self.order.status, Order.Status.REFUNDED)
        self.assertEqual(payment.events.filter(event_type=PaymentEvent.EventType.REFUNDED).count(), 1)
        mock_delay.assert_called_once_with("refund_processed", self.order.id)

        second = self.client.post(
            "/api/v1/payments/refund/",
            {"order_id": self.order.id},
            format="json",
        )
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(second.data["detail"], "Order already refunded.")
        self.assertEqual(payment.events.filter(event_type=PaymentEvent.EventType.REPLAY).count(), 1)
        self.assertEqual(mock_delay.call_count, 1)

    def test_refund_order_rejects_unpaid_order(self):
        Payment.objects.create(
            order=self.order,
            idempotency_key="idem-refund-unpaid",
            razorpay_order_id="order_refund_2",
            amount=99900,
            status=Payment.Status.CREATED,
        )

        response = self.client.post(
            "/api/v1/payments/refund/",
            {"order_id": self.order.id},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["detail"], "Only paid orders can be refunded.")

    def test_payment_verification_logs_failed_event_for_invalid_signature(self):
        payment = Payment.objects.create(
            order=self.order,
            idempotency_key="idem-bad-sig",
            razorpay_order_id="order_bad_sig_1",
            amount=99900,
        )

        response = self.client.post(
            "/api/v1/payments/verify/",
            {
                "razorpay_order_id": "order_bad_sig_1",
                "razorpay_payment_id": "pay_bad_sig_1",
                "razorpay_signature": "invalid-signature",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(payment.events.filter(event_type=PaymentEvent.EventType.PAYMENT_FAILED).count(), 1)
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, Order.PaymentStatus.CANCELLED)
        self.assertEqual(self.order.status, Order.Status.CANCELLED)
        self.assertEqual(
            InventoryReservation.objects.filter(
                order=self.order,
                status=InventoryReservation.Status.RELEASED,
            ).count(),
            1,
        )

    @patch("payments.services.urlopen")
    def test_payment_retry_for_failed_order_creates_new_session(self, mock_urlopen):
        mock_urlopen.return_value = MockHTTPResponse(
            {"id": "order_retry_1", "amount": 99900, "currency": "INR", "status": "created"}
        )
        self.order.payment_status = Order.PaymentStatus.FAILED
        self.order.status = Order.Status.FAILED
        self.order.save(update_fields=["payment_status", "status", "updated_at"])

        response = self.client.post(f"/api/v1/payments/retry/{self.order.id}/")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["retry_attempt"], 1)
        payment = Payment.objects.get(id=response.data["payment_id"])
        self.assertEqual(payment.order_id, self.order.id)
        self.assertEqual(payment.razorpay_order_id, "order_retry_1")
        self.assertEqual(
            payment.events.filter(event_type=PaymentEvent.EventType.RETRY_ATTEMPT).count(),
            1,
        )

    @patch("payments.services.urlopen")
    def test_payment_retry_is_limited_to_three_attempts(self, mock_urlopen):
        self.order.payment_status = Order.PaymentStatus.FAILED
        self.order.status = Order.Status.FAILED
        self.order.save(update_fields=["payment_status", "status", "updated_at"])
        for attempt in range(3):
            mock_urlopen.return_value = MockHTTPResponse(
                {"id": f"order_retry_{attempt}", "amount": 99900, "currency": "INR", "status": "created"}
            )
            response = self.client.post(f"/api/v1/payments/retry/{self.order.id}/")
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        blocked = self.client.post(f"/api/v1/payments/retry/{self.order.id}/")
        self.assertEqual(blocked.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(blocked.data["detail"], "Maximum payment retry attempts reached.")

    @patch("payments.services.urlopen")
    def test_payment_retry_rejects_paid_order(self, mock_urlopen):
        self.order.payment_status = Order.PaymentStatus.PAID
        self.order.status = Order.Status.PAID
        self.order.save(update_fields=["payment_status", "status", "updated_at"])

        response = self.client.post(f"/api/v1/payments/retry/{self.order.id}/")

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data["detail"], "Payment already completed for this order.")
        self.assertEqual(mock_urlopen.call_count, 0)

    def test_payment_event_is_immutable(self):
        payment = Payment.objects.create(
            order=self.order,
            idempotency_key="idem-immutable",
            razorpay_order_id="order_immutable_1",
            amount=99900,
        )
        event = PaymentEvent.objects.create(payment=payment, event_type=PaymentEvent.EventType.CREATED)
        event.metadata = {"changed": True}
        with self.assertRaises(ValidationError):
            event.save()
        with self.assertRaises(ValidationError):
            event.delete()

    def test_payment_event_rejects_queryset_update_and_delete(self):
        payment = Payment.objects.create(
            order=self.order,
            idempotency_key="idem-immutable-db",
            razorpay_order_id="order_immutable_db_1",
            amount=99900,
        )
        event = PaymentEvent.objects.create(payment=payment, event_type=PaymentEvent.EventType.CREATED)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                PaymentEvent.objects.filter(id=event.id).update(metadata={"changed": True})
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                PaymentEvent.objects.filter(id=event.id).delete()
