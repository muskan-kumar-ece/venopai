"""
Payment domain services.

This module encapsulates the business logic that was previously mixed into
``payments/views.py``. Views remain thin HTTP handlers; all side-effect
operations (stock deduction, referral reward issuing, Razorpay API calls)
live here and can be unit-tested without HTTP context.
"""

import base64
import hashlib
import hmac
import json
import logging
from datetime import timedelta
from decimal import Decimal
from uuid import uuid4
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.db import IntegrityError
from django.utils import timezone

from orders.models import Coupon, Order
from users.models import Referral

logger = logging.getLogger(__name__)

MAX_CODE_GENERATION_ATTEMPTS = 5
MAX_RETRY_ATTEMPTS = 3
# Number of hex characters appended to referral coupon codes (e.g. "REF" + 12 hex chars = 15-char code).
REFERRAL_COUPON_CODE_HEX_LENGTH = 12


# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------


class RazorpayIntegrationError(Exception):
    """Raised when the Razorpay HTTP call fails for any reason."""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def compute_signature(message: str, secret: str) -> str:
    """Return the HMAC-SHA256 hex digest of *message* signed with *secret*.

    Both *message* and *secret* must be non-empty strings. Passing ``None``
    or an empty value is a programming error and will raise ``ValueError``.
    """
    if not message or not secret:
        raise ValueError("compute_signature requires non-empty message and secret")
    return hmac.new(secret.encode(), msg=message.encode(), digestmod=hashlib.sha256).hexdigest()


def payment_entity(payload: dict) -> dict:
    """Safely extract the payment entity from a Razorpay webhook payload."""
    return (((payload.get("payload") or {}).get("payment") or {}).get("entity") or {})


# ---------------------------------------------------------------------------
# Domain services
# ---------------------------------------------------------------------------


def deduct_order_stock(order: Order) -> None:
    """
    Atomically deduct product stock for all items in *order*.

    Raises ``ValidationError`` if any item has insufficient stock.
    Idempotent: a second call on an order with ``stock_deducted=True`` is a no-op.
    """
    if order.stock_deducted:
        return
    from orders.inventory import finalize_order_inventory
    finalize_order_inventory(order)


def issue_referral_reward(order: Order) -> None:
    """
    Issue a referral reward coupon to the referrer when *order* is the
    referred user's first paid order.

    Idempotent: does nothing if the reward was already issued.
    """
    referral = (
        Referral.objects.select_for_update()
        .select_related("referrer", "referred_user")
        .filter(referred_user=order.user)
        .first()
    )
    if not referral or referral.reward_issued:
        return

    has_previous_paid_order = (
        Order.objects.filter(user=order.user, payment_status=Order.PaymentStatus.PAID)
        .exclude(id=order.id)
        .exists()
    )
    if has_previous_paid_order:
        return

    now = timezone.now()
    for _ in range(MAX_CODE_GENERATION_ATTEMPTS):
        coupon_code = f"REF{uuid4().hex[:REFERRAL_COUPON_CODE_HEX_LENGTH]}".upper()
        try:
            Coupon.objects.create(
                code=coupon_code,
                discount_type=Coupon.DiscountType.FIXED,
                discount_value=Decimal("100.00"),
                max_uses=1,
                per_user_limit=1,
                eligible_user=referral.referrer,
                valid_from=now,
                valid_until=now + timedelta(days=30),
                is_active=True,
            )
            break
        except IntegrityError:
            continue
    else:
        raise IntegrityError("Unable to generate unique reward coupon code.")

    referral.reward_issued = True
    referral.save(update_fields=["reward_issued"])


def create_razorpay_order(amount: int, currency: str, receipt: str) -> dict:
    """
    Call the Razorpay Orders API and return the response dict.

    Args:
        amount:   Amount in the smallest currency unit (paise for INR).
        currency: Three-letter ISO 4217 currency code.
        receipt:  Merchant receipt identifier (used for reconciliation).

    Raises:
        RazorpayIntegrationError: on any network or parse failure.
    """
    payload = json.dumps(
        {
            "amount": amount,
            "currency": currency,
            "receipt": receipt,
            "payment_capture": 1,
        }
    ).encode()
    credentials = f"{settings.RAZORPAY_KEY_ID}:{settings.RAZORPAY_KEY_SECRET}".encode()
    req = Request(
        f"{settings.RAZORPAY_API_BASE_URL.rstrip('/')}/orders",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Basic {base64.b64encode(credentials).decode()}",
        },
        method="POST",
    )
    try:
        with urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode())
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        logger.error("Razorpay create-order API call failed receipt=%s: %s", receipt, exc)
        raise RazorpayIntegrationError("Failed to create Razorpay order") from exc
