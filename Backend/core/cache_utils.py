from django.core.cache import cache


def cache_get(key, default=None):
    try:
        return cache.get(key, default)
    except Exception:
        return default


def cache_set(key, value, timeout):
    try:
        cache.set(key, value, timeout=timeout)
        return True
    except Exception:
        return False


def cache_add(key, value, timeout):
    try:
        return cache.add(key, value, timeout=timeout)
    except Exception:
        return False


def cache_delete(key):
    try:
        cache.delete(key)
        return True
    except Exception:
        return False


def cache_delete_pattern(pattern: str):
    try:
        delete_pattern = getattr(cache, "delete_pattern", None)
        if callable(delete_pattern):
            delete_pattern(pattern)
            return True
        return False
    except Exception:
        return False


def invalidate_catalog_cache():
    # Works for django-redis. For non-pattern backends this is a no-op.
    cache_delete_pattern("product_list:*")
    cache_delete_pattern("product_detail:*")
    cache_delete("category_list:active")
    cache_delete("homepage:catalog:v1")
