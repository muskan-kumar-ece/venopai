import hashlib
import hmac
import logging
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from uuid import uuid4
import sentry_sdk

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.throttles import PaymentRateThrottle, WebhookRateThrottle
from core.observability import bind_context, log_event, metric_incr
from orders.cart_services import finalize_cart_after_payment
from orders.inventory import release_order_inventory
from orders.tasks import send_order_email_task
from orders.models import Order

from .models import Payment, PaymentEvent, PaymentWebhookEvent, PaymentWebhookRetry
from .services import (
    MAX_RETRY_ATTEMPTS,
    RazorpayIntegrationError,
    compute_signature,
    create_razorpay_order,
    deduct_order_stock,
    issue_referral_reward,
    payment_entity,
)

logger = logging.getLogger(__name__)


class CreateRazorpayOrderView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [PaymentRateThrottle]

    def post(self, request):
        if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
            logger.error(
                "Razorpay key configuration is missing: key_id=%s key_secret=%s",
                bool(settings.RAZORPAY_KEY_ID),
                bool(settings.RAZORPAY_KEY_SECRET),
            )
            return Response({"detail": "Payment gateway configuration error."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        order_id = request.data.get("order_id")
        idempotency_key = request.META.get("HTTP_IDEMPOTENCY_KEY") or request.data.get("idempotency_key")
        if not order_id or not idempotency_key:
            return Response(
                {"detail": "order_id and idempotency_key are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            with transaction.atomic():
                order = (
                    Order.objects.select_for_update()
                    .filter(id=order_id, user=request.user)
                    .first()
                )
                if not order:
                    return Response({"detail": "Order not found."}, status=status.HTTP_404_NOT_FOUND)
                if order.payment_status == Order.PaymentStatus.PAID:
                    return Response({"detail": "Order already paid."}, status=status.HTTP_409_CONFLICT)

                existing_payment = Payment.objects.filter(idempotency_key=idempotency_key).first()
                if existing_payment:
                    if existing_payment.order_id != order.id:
                        return Response({"detail": "Idempotency key is already used."}, status=status.HTTP_409_CONFLICT)
                    return Response(
                        {
                            "payment_id": existing_payment.id,
                            "razorpay_order_id": existing_payment.razorpay_order_id,
                            "amount": existing_payment.amount,
                            "currency": existing_payment.currency,
                            "key_id": settings.RAZORPAY_KEY_ID,
                        },
                        status=status.HTTP_200_OK,
                    )

                amount_paise = int((Decimal(order.total_amount) * Decimal("100")).quantize(Decimal("1")))
                razorpay_order = create_razorpay_order(
                    amount=amount_paise,
                    currency="INR",
                    receipt=f"order_{order.id}",
                )

                payment = Payment.objects.create(
                    order=order,
                    idempotency_key=idempotency_key,
                    razorpay_order_id=razorpay_order["id"],
                    amount=razorpay_order.get("amount", amount_paise),
                    currency=razorpay_order.get("currency", "INR"),
                    status=razorpay_order.get("status", Payment.Status.CREATED),
                    raw_response=razorpay_order,
                )
        except (RazorpayIntegrationError, KeyError, InvalidOperation):
            logger.exception("Order creation failed")
            return Response({"detail": "Unable to create payment order."}, status=status.HTTP_502_BAD_GATEWAY)
        except IntegrityError:
            return Response({"detail": "Duplicate payment attempt detected."}, status=status.HTTP_409_CONFLICT)

        return Response(
            {
                "payment_id": payment.id,
                "razorpay_order_id": payment.razorpay_order_id,
                "amount": payment.amount,
                "currency": payment.currency,
                "key_id": settings.RAZORPAY_KEY_ID,
            },
            status=status.HTTP_201_CREATED,
        )


class RetryPaymentView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [PaymentRateThrottle]

    @transaction.atomic
    def post(self, request, order_id):
        if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
            logger.error(
                "Razorpay key configuration is missing: key_id=%s key_secret=%s",
                bool(settings.RAZORPAY_KEY_ID),
                bool(settings.RAZORPAY_KEY_SECRET),
            )
            return Response({"detail": "Payment gateway configuration error."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        order = Order.objects.select_for_update().filter(id=order_id, user=request.user).first()
        if not order:
            return Response({"detail": "Order not found."}, status=status.HTTP_404_NOT_FOUND)
        if order.payment_status == Order.PaymentStatus.PAID:
            return Response({"detail": "Payment already completed for this order."}, status=status.HTTP_409_CONFLICT)
        if order.reservation_expires_at and order.reservation_expires_at < timezone.now():
            release_order_inventory(order, reason="reservation_expired_retry")
            return Response({"detail": "Reservation expired. Restart checkout."}, status=status.HTTP_409_CONFLICT)
        if order.payment_status not in {Order.PaymentStatus.FAILED, Order.PaymentStatus.CANCELLED}:
            return Response({"detail": "Retry is only available for failed payments."}, status=status.HTTP_400_BAD_REQUEST)

        retry_attempt = PaymentEvent.objects.filter(
            payment__order=order,
            event_type=PaymentEvent.EventType.RETRY_ATTEMPT,
        ).count()
        if retry_attempt >= MAX_RETRY_ATTEMPTS:
            return Response({"detail": "Maximum payment retry attempts reached."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            amount_paise = int((Decimal(order.total_amount) * Decimal("100")).quantize(Decimal("1")))
            razorpay_order = create_razorpay_order(
                amount=amount_paise,
                currency="INR",
                receipt=f"order_{order.id}_retry_{retry_attempt + 1}",
            )
            payment = Payment.objects.create(
                order=order,
                idempotency_key=f"retry-{order.id}-{uuid4().hex}",
                razorpay_order_id=razorpay_order["id"],
                amount=razorpay_order.get("amount", amount_paise),
                currency=razorpay_order.get("currency", "INR"),
                status=razorpay_order.get("status", Payment.Status.CREATED),
                raw_response=razorpay_order,
            )
        except (RazorpayIntegrationError, KeyError, InvalidOperation):
            logger.exception("Payment retry failed")
            return Response({"detail": "Unable to create payment retry session."}, status=status.HTTP_502_BAD_GATEWAY)
        except IntegrityError:
            return Response({"detail": "Duplicate payment retry attempt detected."}, status=status.HTTP_409_CONFLICT)

        PaymentEvent.objects.create(
            payment=payment,
            event_type=PaymentEvent.EventType.RETRY_ATTEMPT,
            metadata={"attempt": retry_attempt + 1},
        )

        return Response(
            {
                "payment_id": payment.id,
                "razorpay_order_id": payment.razorpay_order_id,
                "amount": payment.amount,
                "currency": payment.currency,
                "key_id": settings.RAZORPAY_KEY_ID,
                "retry_attempt": retry_attempt + 1,
            },
            status=status.HTTP_201_CREATED,
        )


class VerifyRazorpayPaymentView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [PaymentRateThrottle]

    @transaction.atomic
    def post(self, request):
        razorpay_order_id = request.data.get("razorpay_order_id")
        razorpay_payment_id = request.data.get("razorpay_payment_id")
        razorpay_signature = request.data.get("razorpay_signature")
        if not razorpay_order_id or not razorpay_payment_id or not razorpay_signature:
            return Response({"detail": "Missing payment verification fields."}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            payment = (
                Payment.objects.select_for_update()
                .select_related("order")
                .filter(razorpay_order_id=razorpay_order_id, order__user=request.user)
                .first()
            )
            if not payment:
                return Response({"detail": "Payment not found."}, status=status.HTTP_404_NOT_FOUND)
            bind_context(order_id=payment.order_id, payment_id=payment.id, user_id=request.user.id)
            if payment.order.payment_status == Order.PaymentStatus.PAID:
                finalize_cart_after_payment(payment.order.source_cart)
                PaymentEvent.objects.create(
                    payment=payment,
                    event_type=PaymentEvent.EventType.REPLAY,
                    metadata={"reason": "already_paid"},
                )
                return Response({"detail": "Payment already verified."}, status=status.HTTP_200_OK)
            duplicate = Payment.objects.filter(razorpay_payment_id=razorpay_payment_id).exclude(id=payment.id).exists()
            if duplicate:
                metric_incr("payment.verify.failed")
                PaymentEvent.objects.create(
                    payment=payment,
                    event_type=PaymentEvent.EventType.DUPLICATE,
                    metadata={"razorpay_payment_id": razorpay_payment_id},
                )
                logger.warning("Duplicate Razorpay payment id received: %s", razorpay_payment_id)
                return Response({"detail": "Duplicate payment id."}, status=status.HTTP_409_CONFLICT)

            expected_signature = compute_signature(
                f"{razorpay_order_id}|{razorpay_payment_id}",
                settings.RAZORPAY_KEY_SECRET,
            )
            if not hmac.compare_digest(expected_signature, razorpay_signature):
                metric_incr("payment.verify.failed")
                payment.status = Payment.Status.FAILED
                payment.failure_reason = "Invalid signature"
                payment.save(update_fields=["status", "failure_reason", "updated_at"])
                PaymentEvent.objects.create(
                    payment=payment,
                    event_type=PaymentEvent.EventType.PAYMENT_FAILED,
                    metadata={"reason": "invalid_signature"},
                )
                payment.order.payment_status = Order.PaymentStatus.FAILED
                payment.order.status = Order.Status.FAILED
                payment.order.save(update_fields=["payment_status", "status", "updated_at"])
                release_order_inventory(
                    payment.order,
                    reason="invalid_signature",
                    payment_reference=razorpay_payment_id,
                )
                logger.warning("Payment signature verification failed for order_id=%s", payment.order_id)
                sentry_sdk.capture_message("payment_signature_verification_failed", level="warning")
                return Response({"detail": "Invalid payment signature."}, status=status.HTTP_400_BAD_REQUEST)

            payment.razorpay_payment_id = razorpay_payment_id
            payment.razorpay_signature = razorpay_signature
            payment.order.payment_status = Order.PaymentStatus.PAYMENT_PROCESSING
            payment.order.status = Order.Status.PAYMENT_PROCESSING
            payment.order.save(update_fields=["payment_status", "status", "updated_at"])
            payment.status = Payment.Status.CAPTURED
            payment.verified_at = timezone.now()
            if (
                payment.order.payment_status != Order.PaymentStatus.PAID
                and not payment.order.stock_deducted
            ):
                deduct_order_stock(payment.order)
            payment.save(
                update_fields=[
                    "razorpay_payment_id",
                    "razorpay_signature",
                    "status",
                    "verified_at",
                    "updated_at",
                ]
            )
            payment.order.payment_status = Order.PaymentStatus.PAID
            order_update_fields = ["payment_status", "updated_at"]
            if payment.order.status != Order.Status.PAID:
                payment.order.status = Order.Status.PAID
                order_update_fields.append("status")
            payment.order.save(update_fields=order_update_fields)
            issue_referral_reward(payment.order)
            finalize_cart_after_payment(payment.order.source_cart)
            metric_incr("payment.verify.success")
            metric_incr("checkout.converted")
            log_event("payment_verified", order_id=payment.order_id, payment_id=payment.id)
            PaymentEvent.objects.create(
                payment=payment,
                event_type=PaymentEvent.EventType.PAYMENT_SUCCESS,
                metadata={"razorpay_payment_id": razorpay_payment_id},
            )
            send_order_email_task.delay("payment_success", payment.order.id)

        return Response({"detail": "Payment verified successfully."}, status=status.HTTP_200_OK)


class RefundOrderView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [PaymentRateThrottle]

    @transaction.atomic
    def post(self, request):
        order_id = request.data.get("order_id")
        if not order_id:
            return Response({"detail": "order_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        order = Order.objects.select_for_update().filter(id=order_id, user=request.user).first()
        if not order:
            return Response({"detail": "Order not found."}, status=status.HTTP_404_NOT_FOUND)
        if order.payment_status == Order.PaymentStatus.REFUNDED:
            if order.status != Order.Status.REFUNDED:
                order.status = Order.Status.REFUNDED
                order.save(update_fields=["status", "updated_at"])
            payment = Payment.objects.filter(order=order).order_by("-created_at").first()
            if payment:
                PaymentEvent.objects.create(
                    payment=payment,
                    event_type=PaymentEvent.EventType.REPLAY,
                    metadata={"reason": "already_refunded"},
                )
            return Response({"detail": "Order already refunded."}, status=status.HTTP_200_OK)
        if order.payment_status != Order.PaymentStatus.PAID:
            return Response({"detail": "Only paid orders can be refunded."}, status=status.HTTP_400_BAD_REQUEST)

        payment = (
            Payment.objects.select_for_update()
            .filter(order=order, status=Payment.Status.CAPTURED)
            .order_by("-created_at")
            .first()
        )
        if not payment:
            return Response({"detail": "Captured payment not found for this order."}, status=status.HTTP_400_BAD_REQUEST)

        payment.status = Payment.Status.REFUNDED
        payment.save(update_fields=["status", "updated_at"])
        PaymentEvent.objects.create(
            payment=payment,
            event_type=PaymentEvent.EventType.REFUNDED,
            metadata={"order_id": order.id},
        )
        order.payment_status = Order.PaymentStatus.REFUNDED
        order.status = Order.Status.REFUNDED
        order.save(update_fields=["payment_status", "status", "updated_at"])
        send_order_email_task.delay("refund_processed", order.id)
        return Response({"detail": "Order refunded successfully."}, status=status.HTTP_200_OK)


class RazorpayWebhookView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    throttle_classes = [WebhookRateThrottle]

    def post(self, request):
        if not settings.RAZORPAY_WEBHOOK_SECRET:
            logger.error("Razorpay webhook secret (RAZORPAY_WEBHOOK_SECRET) is not configured")
            return Response({"detail": "Webhook configuration error."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        signature = request.META.get("HTTP_X_RAZORPAY_SIGNATURE", "")
        raw_body = request.body
        expected_signature = hmac.new(
            settings.RAZORPAY_WEBHOOK_SECRET.encode(),
            msg=raw_body,
            digestmod=hashlib.sha256,
        ).hexdigest()
        if not signature or not hmac.compare_digest(expected_signature, signature):
            metric_incr("payment.webhook.failed")
            logger.warning("Invalid Razorpay webhook signature")
            return Response({"detail": "Invalid webhook signature."}, status=status.HTTP_400_BAD_REQUEST)

        event_id = request.META.get("HTTP_X_RAZORPAY_EVENT_ID") or hashlib.sha256(raw_body).hexdigest()
        event, created = PaymentWebhookEvent.objects.get_or_create(
            event_id=event_id,
            defaults={"event_type": request.data.get("event", "")},
        )
        if not created:
            log_event("webhook_replay", event_id=event_id)
            return Response({"detail": "Webhook already processed."}, status=status.HTTP_200_OK)

        event_type = request.data.get("event")
        entity = payment_entity(request.data)
        razorpay_order_id = entity.get("order_id")
        if not razorpay_order_id:
            return Response({"detail": "Webhook accepted."}, status=status.HTTP_200_OK)

        with transaction.atomic():
            payment = Payment.objects.select_for_update().select_related("order").filter(razorpay_order_id=razorpay_order_id).first()
            if not payment:
                logger.error("No payment found for webhook event_id=%s", event_id)
                return Response({"detail": "Webhook accepted."}, status=status.HTTP_200_OK)
            bind_context(order_id=payment.order_id, payment_id=payment.id)

            payment.razorpay_payment_id = entity.get("id") or payment.razorpay_payment_id
            payment.raw_response = request.data
            allowed_order_status_transitions = {
                Order.PaymentStatus.PENDING: {Order.PaymentStatus.PAID, Order.PaymentStatus.FAILED},
                Order.PaymentStatus.PENDING_PAYMENT: {Order.PaymentStatus.PAID, Order.PaymentStatus.FAILED},
                Order.PaymentStatus.PAYMENT_PROCESSING: {Order.PaymentStatus.PAID, Order.PaymentStatus.FAILED},
                Order.PaymentStatus.PAID: set(),
                Order.PaymentStatus.FAILED: set(),
            }
            if event_type == "payment.captured":
                current_status = payment.order.payment_status
                next_status = Order.PaymentStatus.PAID
                if next_status in allowed_order_status_transitions.get(current_status, set()):
                    should_send_payment_email = payment.order.payment_status != next_status
                    payment.order.payment_status = Order.PaymentStatus.PAYMENT_PROCESSING
                    payment.order.status = Order.Status.PAYMENT_PROCESSING
                    payment.order.save(update_fields=["payment_status", "status", "updated_at"])
                    deduct_order_stock(payment.order)
                    payment.status = Payment.Status.CAPTURED
                    payment.verified_at = timezone.now()
                    payment.order.payment_status = next_status
                    order_update_fields = ["payment_status", "updated_at"]
                    if payment.order.status != Order.Status.PAID:
                        payment.order.status = Order.Status.PAID
                        order_update_fields.append("status")
                    payment.order.save(update_fields=order_update_fields)
                    issue_referral_reward(payment.order)
                    metric_incr("checkout.converted")
                    PaymentEvent.objects.create(
                        payment=payment,
                        event_type=PaymentEvent.EventType.PAYMENT_SUCCESS,
                        metadata={"source": "webhook", "razorpay_payment_id": payment.razorpay_payment_id},
                    )
                    if should_send_payment_email:
                        send_order_email_task.delay("payment_success", payment.order.id)
                else:
                    metric_incr("payment.webhook.failed")
                    PaymentWebhookRetry.objects.create(
                        payment=payment,
                        event_id=event_id,
                        event_type=event_type or "",
                        payload=request.data,
                        next_retry_at=timezone.now() + timedelta(minutes=2),
                    )
                    logger.warning(
                        "Ignoring webhook transition %s -> %s for order_id=%s",
                        current_status,
                        next_status,
                        payment.order_id,
                    )
                finalize_cart_after_payment(payment.order.source_cart)
            elif event_type == "payment.failed":
                current_status = payment.order.payment_status
                next_status = Order.PaymentStatus.FAILED
                if next_status in allowed_order_status_transitions.get(current_status, set()):
                    payment.status = Payment.Status.FAILED
                    payment.failure_reason = entity.get("error_description", "")
                    payment.order.payment_status = next_status
                    payment.order.status = Order.Status.FAILED
                    payment.order.save(update_fields=["payment_status", "status", "updated_at"])
                    release_order_inventory(
                        payment.order,
                        reason="payment_failed_webhook",
                        payment_reference=payment.razorpay_payment_id or "",
                    )
                    PaymentEvent.objects.create(
                        payment=payment,
                        event_type=PaymentEvent.EventType.PAYMENT_FAILED,
                        metadata={"source": "webhook", "reason": payment.failure_reason or "payment_failed"},
                    )
                    logger.error("Payment failed via webhook for order_id=%s", payment.order_id)
                    sentry_sdk.capture_message("payment_failed_webhook", level="warning")
                else:
                    metric_incr("payment.webhook.failed")
                    PaymentWebhookRetry.objects.create(
                        payment=payment,
                        event_id=event_id,
                        event_type=event_type or "",
                        payload=request.data,
                        next_retry_at=timezone.now() + timedelta(minutes=2),
                    )
                    logger.warning(
                        "Ignoring webhook transition %s -> %s for order_id=%s",
                        current_status,
                        next_status,
                        payment.order_id,
                    )
            elif event_type == "payment.authorized":
                payment.status = Payment.Status.AUTHORIZED
            payment.save()

        return Response({"detail": "Webhook processed."}, status=status.HTTP_200_OK)
