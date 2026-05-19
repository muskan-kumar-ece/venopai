from datetime import timedelta
import sentry_sdk

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from products.models import Product
from core.observability import log_event, metric_incr

from .models import InventoryAuditLog, InventoryReservation, Order

DEFAULT_RESERVATION_TTL_MINUTES = 15


def _reservation_ttl_minutes():
    return int(getattr(settings, "INVENTORY_RESERVATION_TTL_MINUTES", DEFAULT_RESERVATION_TTL_MINUTES))


def reserve_order_inventory(order: Order) -> None:
    if order.inventory_reservations.filter(status=InventoryReservation.Status.ACTIVE).exists():
        return

    now = timezone.now()
    expires_at = now + timedelta(minutes=_reservation_ttl_minutes())
    order_items = list(order.items.select_related("product").all())
    product_ids = [item.product_id for item in order_items]
    products = {
        p.id: p for p in Product.objects.select_for_update().filter(id__in=product_ids, is_active=True)
    }

    errors = []
    for item in order_items:
        product = products.get(item.product_id)
        if not product:
            errors.append({"product_id": item.product_id, "reason": "unavailable"})
            continue
        active_reserved = sum(
            InventoryReservation.objects.select_for_update()
            .filter(product_id=item.product_id, status=InventoryReservation.Status.ACTIVE)
            .exclude(order_id=order.id)
            .values_list("quantity", flat=True)
        )
        available = product.stock_quantity - active_reserved
        if available < item.quantity:
            errors.append(
                {
                    "product_id": item.product_id,
                    "reason": "insufficient_stock",
                    "available": max(available, 0),
                    "requested": item.quantity,
                }
            )

    if errors:
        metric_incr("reservation.failed")
        raise ValidationError({"detail": "Cart contains unavailable items.", "items": errors})

    for item in order_items:
        product = products[item.product_id]
        InventoryReservation.objects.create(
            order=order,
            product_id=item.product_id,
            quantity=item.quantity,
            status=InventoryReservation.Status.ACTIVE,
            expires_at=expires_at,
        )
        InventoryAuditLog.objects.create(
            product=product,
            order=order,
            reason=InventoryAuditLog.Reason.RESERVE,
            before_quantity=product.stock_quantity,
            after_quantity=product.stock_quantity,
            delta=0,
            metadata={"reserved_quantity": item.quantity},
        )

    order.reservation_expires_at = expires_at
    order.status = Order.Status.PENDING_PAYMENT
    order.payment_status = Order.PaymentStatus.PENDING_PAYMENT
    order.save(update_fields=["reservation_expires_at", "status", "payment_status", "updated_at"])
    log_event("inventory_reserved", order_id=order.id, expires_at=expires_at.isoformat())


def release_order_inventory(order: Order, *, reason: str, payment_reference: str = "") -> int:
    now = timezone.now()
    with transaction.atomic():
        reservations = list(
            InventoryReservation.objects.select_for_update()
            .select_related("product")
            .filter(order=order, status=InventoryReservation.Status.ACTIVE)
        )
        for reservation in reservations:
            product = reservation.product
            before_qty = product.stock_quantity
            after_qty = before_qty
            InventoryAuditLog.objects.create(
                product=product,
                order=order,
                payment_reference=payment_reference,
                reason=InventoryAuditLog.Reason.RELEASE,
                before_quantity=before_qty,
                after_quantity=after_qty,
                delta=0,
                metadata={"reservation_id": reservation.id, "release_reason": reason},
            )
            reservation.status = InventoryReservation.Status.RELEASED
            reservation.released_at = now
            reservation.save(update_fields=["status", "released_at", "updated_at"])

        if reservations:
            if reason in {"reservation_expired", "stale_pending_order_cleanup"}:
                metric_incr("reservation.timeout")
            order.reservation_released_at = now
            if order.payment_status != Order.PaymentStatus.PAID:
                order.payment_status = Order.PaymentStatus.CANCELLED
                order.status = Order.Status.CANCELLED
            order.save(update_fields=["reservation_released_at", "payment_status", "status", "updated_at"])
            log_event("inventory_released", order_id=order.id, reason=reason, count=len(reservations))
    return len(reservations)


def finalize_order_inventory(order: Order, *, payment_reference: str = "") -> None:
    now = timezone.now()
    reservations = list(
        InventoryReservation.objects.select_for_update()
        .select_related("product")
        .filter(order=order, status=InventoryReservation.Status.ACTIVE)
    )
    for reservation in reservations:
        product = reservation.product
        before_qty = product.stock_quantity
        if before_qty < reservation.quantity:
            sentry_sdk.capture_message("inventory_finalize_insufficient_stock", level="error")
            raise ValidationError({"detail": "Insufficient stock while finalizing payment."})
        product.stock_quantity = before_qty - reservation.quantity
        product.save(update_fields=["stock_quantity", "updated_at"])
        InventoryAuditLog.objects.create(
            product=product,
            order=order,
            payment_reference=payment_reference,
            reason=InventoryAuditLog.Reason.FINALIZE,
            before_quantity=before_qty,
            after_quantity=product.stock_quantity,
            delta=-reservation.quantity,
            metadata={"reservation_id": reservation.id},
        )
        reservation.status = InventoryReservation.Status.FINALIZED
        reservation.finalized_at = now
        reservation.save(update_fields=["status", "finalized_at", "updated_at"])

    order.stock_deducted = True
    order.reservation_released_at = now
    order.save(update_fields=["stock_deducted", "reservation_released_at", "updated_at"])


def expire_stale_reservations(*, now=None) -> int:
    now = now or timezone.now()
    expired_orders = (
        Order.objects.select_for_update()
        .filter(
            payment_status__in=[Order.PaymentStatus.PENDING, Order.PaymentStatus.PENDING_PAYMENT, Order.PaymentStatus.PAYMENT_PROCESSING],
            reservation_expires_at__lt=now,
        )
        .distinct()
    )
    count = 0
    for order in expired_orders:
        count += release_order_inventory(order, reason="reservation_expired")
    stale_reservations = InventoryReservation.objects.select_for_update().filter(
        status=InventoryReservation.Status.ACTIVE,
        expires_at__lt=now,
    )
    for reservation in stale_reservations:
        reservation.status = InventoryReservation.Status.EXPIRED
        reservation.released_at = now
        reservation.save(update_fields=["status", "released_at", "updated_at"])
    return count
