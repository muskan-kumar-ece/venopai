import json
import logging
import time
from typing import Any

from django.core.cache import cache

from .log_filters import get_context, set_context

logger = logging.getLogger("observability")

METRIC_PREFIX = "metrics:"
DEFAULT_TTL_SECONDS = 60 * 60 * 24 * 7


def bind_context(**kwargs: Any) -> None:
    current = get_context()
    current.update({k: v for k, v in kwargs.items() if v is not None})
    set_context(**current)


def metric_incr(name: str, value: int = 1) -> int:
    key = f"{METRIC_PREFIX}{name}"
    try:
        cache.add(key, 0, timeout=DEFAULT_TTL_SECONDS)
        return cache.incr(key, value)
    except Exception:
        logger.exception("metric_increment_failed", extra={"metric_name": name, "metric_value": value})
        return 0


def metric_observe_ms(name: str, duration_ms: float) -> None:
    metric_incr(f"{name}.count", 1)
    metric_incr(f"{name}.sum_ms", int(duration_ms))


def metrics_snapshot() -> dict[str, int]:
    # Fixed keys for operational dashboards.
    keys = [
        "checkout.started",
        "checkout.converted",
        "checkout.failed",
        "payment.verify.success",
        "payment.verify.failed",
        "payment.webhook.failed",
        "reservation.failed",
        "reservation.timeout",
        "auth.refresh.attempt",
        "auth.refresh.failed",
        "api.latency.count",
        "api.latency.sum_ms",
        "rate_limit.hit",
    ]
    payload = {}
    for name in keys:
        payload[name] = int(cache.get(f"{METRIC_PREFIX}{name}", 0) or 0)
    return payload


def log_event(event: str, level: str = "info", **fields: Any) -> None:
    msg = json.dumps({"event": event, **fields}, default=str)
    if level == "error":
        logger.error(msg)
    elif level == "warning":
        logger.warning(msg)
    else:
        logger.info(msg)


def timed(name: str):
    def _decorator(func):
        def _wrapped(*args, **kwargs):
            start = time.monotonic()
            try:
                return func(*args, **kwargs)
            finally:
                metric_observe_ms(name, (time.monotonic() - start) * 1000)

        return _wrapped

    return _decorator
