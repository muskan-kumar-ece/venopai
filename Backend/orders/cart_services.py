from django.db import IntegrityError
from django.db.models import Prefetch

from products.models import Product

from .models import Cart, CartItem


def active_cart_items_queryset():
    return CartItem.objects.select_related("product", "product__category").prefetch_related("product__images")


def get_active_cart_for_user(user):
    return (
        Cart.objects.filter(user=user, is_active=True)
        .prefetch_related(Prefetch("items", queryset=active_cart_items_queryset()))
        .first()
    )


def get_or_create_active_cart(user):
    cart = get_active_cart_for_user(user)
    if cart is not None:
        return cart
    try:
        return Cart.objects.create(user=user, is_active=True)
    except IntegrityError:
        return get_active_cart_for_user(user)


def clear_active_cart_items(user):
    cart = Cart.objects.filter(user=user, is_active=True).first()
    if cart is None:
        return 0
    deleted_count, _ = cart.items.all().delete()
    return deleted_count


def finalize_cart_after_payment(cart):
    """
    Clear and deactivate a cart after successful payment.

    Idempotent: safe to call multiple times; returns the current active cart.
    """
    if cart is None:
        return None

    cart = Cart.objects.select_for_update().filter(pk=cart.pk).first()
    if cart is None:
        return None

    cart.items.all().delete()
    if cart.is_active:
        cart.is_active = False
        cart.save(update_fields=["is_active", "updated_at"])

    return get_or_create_active_cart(cart.user)
