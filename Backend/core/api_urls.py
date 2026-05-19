from django.urls import include, path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from core.health import HealthCheckView, StartupReadinessView
from core.observability import log_event, metric_incr
from core.observability_views import MetricsSnapshotView
from core.throttles import AuthTokenThrottle
from core.cache_utils import cache_add, cache_get, cache_set
from orders.views import AdminAnalyticsView
from products.views import ProductSearchSuggestionsView, ProductSearchView
from rest_framework.response import Response
from users.models import AuthEvent


class ThrottledTokenObtainPairView(TokenObtainPairView):
    throttle_classes = [AuthTokenThrottle]
    MAX_LOGIN_FAILURES = 8
    LOCK_SECONDS = 60 * 15

    def _lock_key(self, request):
        username = str(request.data.get("email") or request.data.get("username") or "").lower()
        ip = request.META.get("REMOTE_ADDR", "unknown")
        return f"auth:login-lock:{ip}:{username}"

    def _failure_key(self, request):
        username = str(request.data.get("email") or request.data.get("username") or "").lower()
        ip = request.META.get("REMOTE_ADDR", "unknown")
        return f"auth:login-fail:{ip}:{username}"

    def post(self, request, *args, **kwargs):
        lock_key = self._lock_key(request)
        if cache_get(lock_key):
            metric_incr("auth.login.locked")
            return Response({"detail": "Too many failed login attempts. Try again later."}, status=429)
        AuthEvent.objects.create(
            event_type=AuthEvent.EventType.LOGIN_ATTEMPT,
            request_id=getattr(request, "request_id", ""),
            metadata={"path": request.path},
        )
        response: Response = super().post(request, *args, **kwargs)
        if response.status_code >= 400:
            failure_key = self._failure_key(request)
            failures = int(cache_get(failure_key, 0) or 0) + 1
            cache_set(failure_key, failures, timeout=self.LOCK_SECONDS)
            if failures >= self.MAX_LOGIN_FAILURES:
                cache_add(lock_key, "1", timeout=self.LOCK_SECONDS)
            AuthEvent.objects.create(
                event_type=AuthEvent.EventType.LOGIN_FAILED,
                request_id=getattr(request, "request_id", ""),
                metadata={"status_code": response.status_code},
            )
        else:
            cache_set(self._failure_key(request), 0, timeout=60)
            AuthEvent.objects.create(
                event_type=AuthEvent.EventType.LOGIN_SUCCESS,
                request_id=getattr(request, "request_id", ""),
            )
        return response


class ThrottledTokenRefreshView(TokenRefreshView):
    throttle_classes = [AuthTokenThrottle]

    def post(self, request, *args, **kwargs):
        metric_incr("auth.refresh.attempt")
        AuthEvent.objects.create(
            event_type=AuthEvent.EventType.TOKEN_REFRESH_ATTEMPT,
            request_id=getattr(request, "request_id", ""),
            metadata={"path": request.path},
        )
        try:
            response: Response = super().post(request, *args, **kwargs)
            if response.status_code >= 400:
                metric_incr("auth.refresh.failed")
                log_event("auth_refresh_failed", level="warning", status_code=response.status_code)
                AuthEvent.objects.create(
                    event_type=AuthEvent.EventType.TOKEN_REFRESH_FAILED,
                    request_id=getattr(request, "request_id", ""),
                    metadata={"status_code": response.status_code},
                )
            else:
                AuthEvent.objects.create(
                    event_type=AuthEvent.EventType.TOKEN_REFRESH_SUCCESS,
                    request_id=getattr(request, "request_id", ""),
                )
            return response
        except Exception:
            metric_incr("auth.refresh.failed")
            log_event("auth_refresh_exception", level="error")
            AuthEvent.objects.create(
                event_type=AuthEvent.EventType.TOKEN_REFRESH_FAILED,
                request_id=getattr(request, "request_id", ""),
                metadata={"error": "exception"},
            )
            raise


urlpatterns = [
    path("health/", HealthCheckView.as_view(), name="health-check"),
    path("health/startup/", StartupReadinessView.as_view(), name="health-startup"),
    path("observability/metrics/", MetricsSnapshotView.as_view(), name="metrics-snapshot"),
    path("auth/token/", ThrottledTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/token/refresh/", ThrottledTokenRefreshView.as_view(), name="token_refresh"),
    path("admin/analytics/", AdminAnalyticsView.as_view(), name="admin-analytics"),
    path("search/", ProductSearchView.as_view(), name="product-search"),
    path("search", ProductSearchView.as_view(), name="product-search-no-slash"),
    path("search/suggestions/", ProductSearchSuggestionsView.as_view(), name="product-search-suggestions"),
    path("search/suggestions", ProductSearchSuggestionsView.as_view(), name="product-search-suggestions-no-slash"),
    path("users/", include("users.urls")),
    path("products/", include("products.urls")),
    path("flash-sales/", include("products.flash_sale_urls")),
    path("reviews/", include("products.review_urls")),
    path("orders/", include("orders.urls")),
    path("payments/", include("payments.urls")),
    path("wishlist/", include("apps.wishlist.urls")),
    path("chatbot/", include("apps.chatbot.urls")),
    path("price-watch/", include("apps.price_watch.urls")),
    path("vendors/", include("vendors.urls")),
    path("admin/", include("adminpanel.urls")),
]
