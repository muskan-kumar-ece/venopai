from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from core.cache_utils import invalidate_catalog_cache

from .models import Category, Product, ProductImage


@receiver(post_save, sender=Product)
@receiver(post_delete, sender=Product)
@receiver(post_save, sender=Category)
@receiver(post_delete, sender=Category)
@receiver(post_save, sender=ProductImage)
@receiver(post_delete, sender=ProductImage)
def invalidate_product_related_cache(**kwargs):
    invalidate_catalog_cache()
