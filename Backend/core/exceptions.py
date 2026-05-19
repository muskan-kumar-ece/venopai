from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed, NotAuthenticated
from rest_framework.views import exception_handler
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework.exceptions import Throttled
from core.observability import log_event, metric_incr


def api_exception_handler(exc, context):
    """
    Normalize authentication-related errors into a consistent response payload.

    This keeps frontend refresh logic predictable by returning structured auth
    error codes for missing, invalid, or expired tokens.
    """
    response = exception_handler(exc, context)
    if response is None:
        return None

    if isinstance(exc, (AuthenticationFailed, NotAuthenticated)):
        detail = str(getattr(exc, "detail", "Authentication failed."))
        response.data = {
            "detail": detail,
            "code": "auth_required" if isinstance(exc, NotAuthenticated) else "auth_failed",
        }
        response.status_code = status.HTTP_401_UNAUTHORIZED
        return response

    if isinstance(exc, (InvalidToken, TokenError)):
        detail = response.data.get("detail") if isinstance(response.data, dict) else None
        response.data = {
            "detail": detail or "Token is invalid or expired.",
            "code": "token_not_valid",
        }
        response.status_code = status.HTTP_401_UNAUTHORIZED
        return response

    if isinstance(exc, Throttled):
        metric_incr("rate_limit.hit")
        log_event("rate_limit_hit", level="warning", wait=getattr(exc, "wait", None))
        return response

    return response
