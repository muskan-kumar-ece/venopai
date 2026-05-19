import base64
import json
import logging
import time
from urllib.request import Request, urlopen

from django.conf import settings
from core.cache_utils import cache_get, cache_set
from django.db import OperationalError, connection
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from core.celery import app as celery_app
from core.cache_utils import cache_get, cache_set

logger = logging.getLogger(__name__)


def _probe_database():
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
    return {"status": "ok"}


def _probe_cache():
    cache_key = "health_probe"
    cache_set(cache_key, "1", timeout=5)
    if cache_get(cache_key) != "1":
        raise RuntimeError("cache round-trip mismatch")
    return {"status": "ok"}


def _probe_queue():
    if not settings.CELERY_BROKER_URL:
        return {"status": "skipped", "reason": "CELERY_BROKER_URL not configured"}
    conn = celery_app.connection_for_read()
    conn.ensure_connection(max_retries=1)
    return {"status": "ok"}


def _probe_payment_gateway():
    if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
        return {"status": "skipped", "reason": "Razorpay credentials not configured"}
    credentials = f"{settings.RAZORPAY_KEY_ID}:{settings.RAZORPAY_KEY_SECRET}".encode()
    req = Request(
        f"{settings.RAZORPAY_API_BASE_URL.rstrip('/')}/orders?count=1",
        headers={
            "Authorization": f"Basic {base64.b64encode(credentials).decode()}",
            "Content-Type": "application/json",
        },
        method="GET",
    )
    with urlopen(req, timeout=5) as response:
        body = response.read().decode() or "{}"
        json.loads(body)
    return {"status": "ok"}


def _run_checks(include_external: bool):
    checks = {
        "database": _probe_database,
        "redis_cache": _probe_cache,
        "queue": _probe_queue,
    }
    if include_external:
        checks["payment_gateway"] = _probe_payment_gateway
    results = {}
    degraded = False
    for name, fn in checks.items():
        try:
            results[name] = fn()
        except Exception as exc:  # noqa: BLE001
            results[name] = {"status": "error", "reason": str(exc)}
            degraded = True
            logger.exception("health_check_failed", extra={"path": name})
    return results, degraded


class HealthCheckView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        cached = cache_get("health:last")
        if cached is not None:
            return Response(cached, status=200 if cached.get("status") == "ok" else 503)
        start = time.monotonic()
        checks, degraded = _run_checks(include_external=False)
        elapsed_ms = round((time.monotonic() - start) * 1000, 2)
        payload = {
            "status": "ok" if not degraded else "error",
            "checks": checks,
            "response_time_ms": elapsed_ms,
        }
        cache_set("health:last", payload, timeout=getattr(settings, "CACHE_TTL_HEALTH", 10))
        return Response(payload, status=200 if not degraded else 503)


class StartupReadinessView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        start = time.monotonic()
        checks, degraded = _run_checks(include_external=True)
        elapsed_ms = round((time.monotonic() - start) * 1000, 2)
        return Response(
            {
                "status": "ok" if not degraded else "error",
                "checks": checks,
                "response_time_ms": elapsed_ms,
            },
            status=200 if not degraded else 503,
        )
