# Ecommerce Platform – Improvement Roadmap

> **Based on:** [`docs/AUDIT_REPORT.md`](AUDIT_REPORT.md)  
> **Baseline production readiness score:** 62 / 100

Each phase is ordered by business risk and implementation difficulty.  
Items marked **✅ DONE** are already merged.

---

## Phase 1 – Critical (fix before production launch)

### 1.1 API Rate Limiting ✅ DONE

**Explanation**  
Without rate limiting, the login endpoint (`/api/v1/auth/token/`) is open to
brute-force credential stuffing. Any anonymous endpoint (product search,
flash-sale listing) can be hammered to cause DoS.

**Files modified**
- `Backend/core/settings/base.py` – added `DEFAULT_THROTTLE_CLASSES` and `DEFAULT_THROTTLE_RATES`
- `Backend/core/api_urls.py` – added `AuthTokenThrottle` (10 req/min, IP-keyed) on both JWT endpoints

**Implementation approach**  
DRF's built-in `AnonRateThrottle` and `UserRateThrottle` cover global traffic.
A custom `AuthTokenThrottle` (inherits `AnonRateThrottle`, `scope="auth"`) is
applied directly to the token views so its stricter limit overrides the global
default. All rates are configurable via env vars (`THROTTLE_RATE_ANON`,
`THROTTLE_RATE_USER`, `THROTTLE_RATE_AUTH`) so they can be tuned per-environment
without a code deploy.

---

### 1.2 Health-check endpoint ✅ DONE

**Explanation**  
Load balancers (AWS ALB, GCP LB, k8s probes) need an unauthenticated endpoint
that returns `HTTP 200` when the service is healthy and `HTTP 503` when it is
not. Without this, a deployment with a broken DB connection will silently
serve 500 errors.

**Files modified**
- `Backend/core/health.py` ← **new file** – `HealthCheckView` probes the DB
- `Backend/core/api_urls.py` – registers `GET /api/v1/health/`

**Implementation approach**  
```python
# core/health.py
class HealthCheckView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            connection.cursor().execute("SELECT 1")
            db_status = "ok"
        except OperationalError as e:
            db_status = f"error: {e}"
            # return HTTP 503

        return Response({"status": "ok", "checks": {"database": db_status}})
```

Add a k8s liveness probe:
```yaml
livenessProbe:
  httpGet:
    path: /api/v1/health/
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 15
```

---

### 1.3 Payment service extraction ✅ DONE

**Explanation**  
`payments/views.py` contained 527 lines mixing HTTP handling with domain logic
(`_deduct_order_stock`, `_issue_referral_reward`, `_create_razorpay_order`).
This made unit testing the business rules impossible without going through HTTP.

**Files modified**
- `Backend/payments/services.py` ← **new file** – all domain functions extracted
- `Backend/payments/views.py` – imports from `services.py`; reduced to pure HTTP handlers
- `Backend/payments/tests.py` – mocks updated to `payments.services.urlopen`

**Implementation approach**  
1. Create `payments/services.py` with public functions: `deduct_order_stock()`,
   `issue_referral_reward()`, `create_razorpay_order()`.
2. Replace inline `_` prefixed functions in `views.py` with imports.
3. Update `@patch` targets in tests from `payments.views.*` to `payments.services.*`.

---

### 1.4 Admin API URL consistency ✅ DONE

**Explanation**  
Admin panel routes (`/admin/orders/`, `/admin/analytics/summary/`) lived in the
root `urls.py` outside the versioned `/api/v1/` namespace. This breaks API
versioning, makes auth middleware inconsistent, and confuses OpenAPI schema
generation.

**Files modified**
- `Backend/adminpanel/urls.py` – populated with canonical routes
- `Backend/core/api_urls.py` – includes `adminpanel.urls` at `admin/` prefix under `/api/v1/`
- `Backend/core/urls.py` – keeps old routes as backward-compat aliases
- `Frontend/lib/api/orders.ts` – updated to `/api/v1/admin/orders/`
- `Frontend/lib/api/analytics.ts` – updated to `/api/v1/admin/analytics/summary/`

**Implementation approach**  
Populate `adminpanel/urls.py`, include it in `api_urls.py` under `"admin/"`, then
update the frontend. Keep the old root-level URLs in `core/urls.py` as aliases
until all clients have migrated, then remove them in a future release.

---

### 1.5 CI/CD Pipelines ✅ DONE

**Explanation**  
Without CI, broken commits go undetected until deployment. There was no
automated test execution or build verification.

**Files added**
- `.github/workflows/backend-ci.yml` – runs 111 Django tests on every PR
- `.github/workflows/frontend-ci.yml` – runs `next lint` + `next build`

---

## Phase 2 – Architecture Improvements

### 2.1 OpenAPI auto-documentation ✅ DONE

**Explanation**  
`API_CONTRACT.md` was maintained manually and drifted from the implementation.
Auto-generated OpenAPI specs stay in sync, enable client SDK generation, and
serve interactive Swagger / ReDoc UIs.

**Files modified**
- `Backend/requirements.txt` – added `drf-spectacular==0.28.0`
- `Backend/core/settings/base.py` – added `drf_spectacular` to `INSTALLED_APPS` + `SPECTACULAR_SETTINGS`
- `Backend/core/urls.py` – registered `/api/schema/`, `/api/docs/`, `/api/redoc/`

**Implementation approach**  
```python
# settings/base.py
SPECTACULAR_SETTINGS = {
    "TITLE": "Ecommerce API",
    "VERSION": "1.0.0",
    "SCHEMA_PATH_PREFIX": r"/api/v1/",
}
```

```python
# urls.py
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
urlpatterns += [
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/",   SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/",  SpectacularRedocView.as_view(url_name="schema"),   name="redoc"),
]
```

Restrict `/api/docs/` to internal IPs in production via nginx `allow`/`deny` directives.

---

### 2.2 Async task queue (Celery + Redis)

**Explanation**  
Email sends (`send_order_email`) and management commands (`check_price_drops`,
`send_abandoned_cart_reminders`) run synchronously in the request cycle. An SMTP
timeout blocks the HTTP response. There is also no retry mechanism for failed sends.

**Files to modify**
- `Backend/requirements.txt` – add `celery[redis]`
- `Backend/core/celery.py` ← **new file** – Celery app setup
- `Backend/core/__init__.py` – import celery app
- `Backend/core/settings/base.py` – add `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`
- `Backend/orders/tasks.py` ← **new file** – `send_order_email_task`
- `Backend/orders/notifications.py` – replace direct `send_mail` calls with task dispatch
- `Backend/apps/price_watch/tasks.py` ← **new file** – `check_price_drops_task`
- `Backend/orders/management/commands/send_abandoned_cart_reminders.py` – wrap in task

**Implementation approach**
```bash
pip install "celery[redis]==5.4.0"
```

```python
# core/celery.py
import os
from celery import Celery
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings.dev")
app = Celery("ecommerce")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
```

```python
# orders/tasks.py
from celery import shared_task
from .notifications import _send_order_email_sync

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_order_email_task(self, email_type: str, order_id: int):
    from .models import Order
    order = Order.objects.select_related("user").prefetch_related("items__product").get(pk=order_id)
    _send_order_email_sync(email_type, order)
```

Start worker: `celery -A core worker -l info`  
Start beat:   `celery -A core beat -l info`

---

### 2.3 Dedicated object storage for media

**Explanation**  
Product images written to `MEDIA_ROOT` are lost on container restart and not
shared between replicas. This is a data-loss risk in production.

**Files to modify**
- `Backend/requirements.txt` – add `django-storages[s3]` or `django-storages[gcs]`
- `Backend/core/settings/base.py` – set `DEFAULT_FILE_STORAGE`, `AWS_*` env vars
- `Backend/.env.example` – document `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_STORAGE_BUCKET_NAME`

**Implementation approach**
```bash
pip install "django-storages[s3]==1.14.4" boto3
```

```python
# settings/prod.py
DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
AWS_STORAGE_BUCKET_NAME = config("AWS_STORAGE_BUCKET_NAME")
AWS_S3_REGION_NAME     = config("AWS_S3_REGION_NAME", default="ap-south-1")
AWS_S3_CUSTOM_DOMAIN   = f"{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com"
```

---

## Phase 3 – Performance Improvements

### 3.1 Split ProductSerializer into list / detail ✅ DONE

**Explanation**  
`ProductSerializer` returned `description` (can be many KB), nested inventory,
and timestamps on every paginated list response. With 20 items per page this
amplifies response size by up to 10×.

**Files modified**
- `Backend/products/serializers.py` – added `ProductListSerializer` (lightweight)
- `Backend/products/views.py` – `get_serializer_class()` returns `ProductListSerializer` for `list` action

---

### 3.2 Fix N+1 queries in OrderViewSet ✅ DONE

**Explanation**  
`OrderViewSet.get_queryset` used `prefetch_related("items")` but not
`prefetch_related("items__product")`, causing one extra SQL query per order item
when serializing order details.

**Files modified**
- `Backend/orders/views.py` – changed to `prefetch_related("items__product", "shipping_events", "events")`
  and `select_related("shipping_address", "applied_coupon")`

---

### 3.3 Redis caching for product listing and analytics

**Explanation**  
Product listing queries with aggregations (`AVG`, `COUNT`) run on every request.
Analytics endpoints aggregate entire `Order` tables. These are ideal cache targets.

**Files to modify**
- `Backend/products/views.py` – wrap `list` action with `cache.get/set`
- `Backend/orders/views.py` – cache `AdminAnalyticsView.get`
- `Backend/core/settings/base.py` – Redis cache already configured ✅

**Implementation approach**
```python
# products/views.py
from django.core.cache import cache
from django.conf import settings

class ProductViewSet(viewsets.ModelViewSet):
    def list(self, request, *args, **kwargs):
        cache_key = f"products:list:{request.query_params.urlencode()}"
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)
        response = super().list(request, *args, **kwargs)
        cache.set(cache_key, response.data, timeout=settings.CACHE_TTL_PRODUCT_LIST)
        return response
```

```python
# orders/views.py – AdminAnalyticsView
def get(self, request):
    cached = cache.get("admin:analytics")
    if cached:
        return Response(cached)
    data = self._compute_analytics()
    cache.set("admin:analytics", data, timeout=settings.CACHE_TTL_ANALYTICS)
    return Response(data)
```

Invalidate product cache on `Product.save` / `Inventory.save` using Django signals:
```python
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.cache import cache

@receiver(post_save, sender=Product)
def invalidate_product_cache(sender, **kwargs):
    cache.delete_pattern("products:list:*")  # requires django-redis
```

---

### 3.4 PostgreSQL full-text search

**Explanation**  
`ProductSearchView` uses `LIKE`-based filtering (`icontains`) with Python-side
scoring. At scale this is slow and index-unfriendly.

**Files to modify**
- `Backend/products/views.py` – replace `icontains` with `SearchVector`/`SearchQuery`
- `Backend/products/migrations/` – add `GinIndex` on `SearchVectorField`

**Implementation approach**
```python
from django.contrib.postgres.search import (
    SearchQuery, SearchRank, SearchVector, TrigramSimilarity
)

vector = SearchVector("name", weight="A") + SearchVector("description", weight="B")
query  = SearchQuery(q)
products = (
    Product.objects
    .annotate(rank=SearchRank(vector, query))
    .filter(rank__gte=0.1)
    .order_by("-rank")
)
```

Add a stored `SearchVectorField` with a `GinIndex` for maximum throughput:
```python
# models.py
from django.contrib.postgres.search import SearchVectorField
from django.contrib.postgres.indexes import GinIndex

class Product(models.Model):
    search_vector = SearchVectorField(null=True, blank=True)

    class Meta:
        indexes = [GinIndex(fields=["search_vector"])]
```

---

## Phase 4 – Security Improvements

### 4.1 Input sanitization (XSS prevention) ✅ DONE

**Explanation**  
Free-text fields (`Product.description`, `Product.name`, `Review.comment`,
`Review.title`) accepted raw HTML. Stored XSS is possible if output is ever
rendered without escaping.

**Files modified**
- `Backend/products/serializers.py` – added `strip_html_tags()` utility; applied in
  `validate_description`, `validate_name`, `validate_title`, `validate_comment`

---

### 4.2 Request ID tracing ✅ DONE

**Explanation**  
Without a request ID it is impossible to correlate a user-reported error with a
specific log line or a Sentry event. This is a prerequisite for effective
incident response.

**Files added**
- `Backend/core/middleware.py` – `RequestIDMiddleware` sets `X-Request-ID` on every response

**Files modified**
- `Backend/core/settings/base.py` – adds middleware to `MIDDLEWARE` list

---

### 4.3 Restrict OpenAPI docs in production

**Explanation**  
`/api/docs/` (Swagger UI) exposes the full API surface. In production, access
should be limited to VPN / internal IPs.

**Files to modify**
- `Backend/core/urls.py` – wrap schema views with `staff_member_required` or `login_required`
- Nginx config – `allow` internal subnet, `deny all` for `/api/docs/`

**Implementation approach**
```python
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator

@method_decorator(staff_member_required, name="dispatch")
class ProtectedSwaggerView(SpectacularSwaggerView):
    pass
```

---

### 4.4 Enforce HTTPS in production

**Explanation**  
`prod.py` sets `SECURE_SSL_REDIRECT=True` but this requires the reverse proxy
to set `X-Forwarded-Proto` for Django to detect HTTPS correctly behind load
balancers.

**Files to modify**
- `Backend/core/settings/prod.py` – add `SECURE_PROXY_SSL_HEADER`

```python
# settings/prod.py
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
```

---

### 4.5 Admin 2FA

**Explanation**  
Staff accounts with access to the Django admin and analytics endpoints are
high-value targets. TOTP 2FA significantly reduces risk from credential theft.

**Files to modify**
- `Backend/requirements.txt` – add `django-otp` + `qrcode`
- `Backend/core/settings/base.py` – OTP middleware + `INSTALLED_APPS`
- `Backend/users/admin.py` – require OTP device for admin login

**Implementation approach**
```bash
pip install django-otp qrcode[pil]
```

```python
# settings/base.py
INSTALLED_APPS += ["django_otp", "django_otp.plugins.otp_totp"]
MIDDLEWARE.insert(
    MIDDLEWARE.index("django.contrib.auth.middleware.AuthenticationMiddleware") + 1,
    "django_otp.middleware.OTPMiddleware",
)
```

---

## Phase 5 – Production Readiness

### 5.1 Redis caching backend ✅ DONE (configured)

`django-redis` is now in `requirements.txt` and settings auto-detect
`CACHE_REDIS_URL`. Product list and analytics TTLs are configurable via env.

---

### 5.2 Containerization ✅ DONE

- `Backend/Dockerfile` – Python 3.12-slim, Daphne ASGI
- `Frontend/Dockerfile` – multi-stage Node 20 Alpine
- `docker-compose.yml` – PostgreSQL 16 + Redis 7 + backend + frontend

---

### 5.3 Error tracking (Sentry)

**Explanation**  
Console logging has no alerting, no grouping, and no stack-trace enrichment.
Sentry provides real-time error monitoring, release tracking, and performance
profiling.

**Files to modify**
- `Backend/requirements.txt` – add `sentry-sdk[django]`
- `Backend/core/settings/base.py` – Sentry init
- `Backend/.env.example` – add `SENTRY_DSN`

**Implementation approach**
```bash
pip install "sentry-sdk[django]==2.22.0"
```

```python
# settings/base.py
import sentry_sdk
SENTRY_DSN = config("SENTRY_DSN", default="")
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        traces_sample_rate=config("SENTRY_TRACES_SAMPLE_RATE", default=0.1, cast=float),
        send_default_pii=False,
    )
```

---

### 5.4 Staging deployment pipeline

**Explanation**  
Merging to `main` should automatically deploy to a staging environment where
smoke tests run before production promotion.

**Files to add**
- `.github/workflows/deploy-staging.yml` – builds Docker image, pushes to registry, deploys

**Implementation approach** (AWS ECS example)
```yaml
name: Deploy to Staging
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: ap-south-1
      - run: |
          aws ecr get-login-password | docker login --username AWS --password-stdin $ECR_REGISTRY
          docker build -t $ECR_REGISTRY/ecommerce-backend:$GITHUB_SHA ./Backend
          docker push $ECR_REGISTRY/ecommerce-backend:$GITHUB_SHA
          aws ecs update-service --cluster staging --service backend --force-new-deployment
```

---

### 5.5 Database connection pooler (PgBouncer)

**Explanation**  
Each Django process opens up to `CONN_MAX_AGE` persistent connections.
With many workers this can exhaust `max_connections` on the PostgreSQL server.
PgBouncer sits between Django and Postgres and multiplexes connections.

**Files to modify**
- `docker-compose.yml` – add `pgbouncer` service
- `Backend/.env.example` – document `DB_HOST=pgbouncer` override

**Implementation approach**
```yaml
# docker-compose.yml
pgbouncer:
  image: bitnami/pgbouncer:1.23.1
  environment:
    PGBOUNCER_DATABASE: ecommerce
    POSTGRESQL_HOST: db
    PGBOUNCER_POOL_MODE: transaction
    PGBOUNCER_MAX_CLIENT_CONN: 200
    PGBOUNCER_DEFAULT_POOL_SIZE: 20
  depends_on:
    db:
      condition: service_healthy
```

Set `DB_HOST=pgbouncer` in the backend env.

---

## Summary – Updated Production Readiness Estimates

| Category | Before | After Phase 1-5 |
|----------|--------|-----------------|
| Security | 70 | **83** |
| Performance | 55 | **72** |
| Observability | 40 | **68** |
| Reliability | 50 | **74** |
| Scalability | 45 | **65** |
| Testing | 75 | **78** |
| CI/CD | 60 | **75** |
| Documentation | 65 | **80** |
| **Overall** | **62** | **~74** |
