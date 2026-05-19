"""
Request-ID middleware.

Attaches a unique ``X-Request-ID`` header to every HTTP response so that
individual requests can be traced across log lines, Sentry events, and
downstream service calls.

If the incoming request already carries a ``X-Request-ID`` header (e.g. from
a load-balancer or a frontend that generated the ID), that value is reused.
Otherwise a new UUID4 is generated.

The ID is also written into thread-local storage via ``core.log_filters`` so
that every ``logging`` call made during the request automatically includes the
ID in formatted log lines (requires ``RequestIDFilter`` to be wired into
``LOGGING`` — see ``settings/base.py``).
"""

import logging
import time
import uuid

from .log_filters import clear_context, set_context, set_request_id
from .observability import metric_incr, metric_observe_ms

logger = logging.getLogger(__name__)

REQUEST_ID_HEADER = "X-Request-ID"
REQUEST_ID_META_KEY = "HTTP_X_REQUEST_ID"


class RequestIDMiddleware:
    """Assign and propagate a unique request identifier for every HTTP request."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.monotonic()
        request_id = request.META.get(REQUEST_ID_META_KEY) or str(uuid.uuid4())
        request.request_id = request_id

        # Propagate to thread-local so logging filter can read it.
        set_request_id(request_id)
        set_context(
            path=request.path,
            method=request.method,
            user_id=getattr(getattr(request, "user", None), "id", None),
        )

        try:
            response = self.get_response(request)
            return response
        finally:
            elapsed_ms = round((time.monotonic() - start) * 1000, 2)
            metric_observe_ms("api.latency", elapsed_ms)
            status_code = getattr(locals().get("response"), "status_code", 500)
            if status_code == 429:
                metric_incr("rate_limit.hit")
            logger.info(
                "request_completed",
                extra={"status_code": status_code, "latency_ms": elapsed_ms},
            )
            if "response" in locals():
                response[REQUEST_ID_HEADER] = request_id
            clear_context()
