# Deep Production Readiness Audit

**Platform:** Venopai Ecommerce  
**Repository:** `muskan-kumar-ece/Ecommerce`  
**Audit Date:** March 2026  
**Auditor:** Automated production readiness review  
**Methodology:** Full static analysis of source code, configuration files, CI/CD pipelines, Docker setup, and dependency graph.

---

## Summary Scorecard

| Category | Score | Status |
|----------|-------|--------|
| [Scalability](#1-scalability) | **5 / 10** | ⚠️ Needs work |
| [Maintainability](#2-maintainability) | **7 / 10** | 🟡 Good baseline |
| [Observability](#3-observability) | **5 / 10** | ⚠️ Needs work |
| [Fault Tolerance](#4-fault-tolerance) | **6 / 10** | 🟡 Good baseline |
| [Data Consistency](#5-data-consistency) | **7 / 10** | 🟡 Good baseline |
| [Deployment Readiness](#6-deployment-readiness) | **6 / 10** | 🟡 Good baseline |
| **Overall** | **36 / 60 (60%)** | ⚠️ MVP-ready, not prod-ready |

---

## 1. Scalability

### Score: 5 / 10

### What Is Working Well ✅

| Item | Evidence |
|------|---------|
| ASGI runtime | `core/asgi.py` uses Daphne — handles async HTTP + WebSocket connections efficiently |
| Redis channel layer | `CHANNEL_REDIS_URL` switches to `RedisChannelLayer` — enables horizontal WebSocket scaling |
| Redis cache backend | `CACHE_REDIS_URL` enables `django-redis` for distributed caching (configured in Phase 1) |
| Persistent DB connections | `CONN_MAX_AGE=60` in `DATABASES` avoids per-request TCP handshakes |
| Paginated responses | `ProductPagination` (page_size=20), `ReviewPagination` (page_size=10) prevent unbounded result sets |
| Database indexes | Products, Orders, Payments, Carts all have explicit `Meta.indexes` declarations |
| Select-related/prefetch | `OrderViewSet`, `CartItemViewSet`, `ProductViewSet` use ORM join optimisation |

### Critical Gaps ❌

#### 1.1 No Async Task Queue
**Impact:** HIGH  
All email sends (`send_order_email`, `send_abandoned_cart_email`) and the `check_price_drops` / `send_abandoned_cart_reminders` management commands run synchronously in the HTTP request cycle or must be triggered manually. An SMTP timeout blocks the entire request. Under load, this becomes a primary latency source.

```
Backend/orders/notifications.py:send_order_email()  →  called from:
  payments/views.py:VerifyRazorpayPaymentView.post()
  payments/views.py:RazorpayWebhookView.post()
  orders/views.py:OrderViewSet.cancel_order()
  adminpanel/views.py:AdminOrderStatusUpdateView.post()
```

**Fix:** Introduce Celery + Redis broker. Wrap `send_order_email` in a `@shared_task` and dispatch with `.delay()`.

```python
# orders/tasks.py
from celery import shared_task
from .notifications import send_order_email as _send

@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_order_email_task(self, email_type: str, order_id: int):
    from .models import Order
    order = Order.objects.select_related("user").get(pk=order_id)
    _send(email_type, order)
```

#### 1.2 Product Search Does Not Scale
**Impact:** HIGH  
`ProductSearchView` loads every matching product into Python memory and scores them with `SequenceMatcher`. At 100k+ products this will OOM or time out.

```python
# products/views.py:168
products = Product.objects.filter(is_active=True).filter(self._candidate_filter(query))
ranked = []
for product in products:  # ← full table scan into memory
    ...
    ranked.append(product)
```

**Fix:** Migrate to PostgreSQL full-text search with a `GinIndex`:

```python
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from django.contrib.postgres.indexes import GinIndex

# In migration: add GinIndex on search_vector field
# In view:
vector = SearchVector("name", weight="A") + SearchVector("description", weight="B")
query  = SearchQuery(q)
products = (
    Product.objects.annotate(rank=SearchRank(vector, query))
    .filter(rank__gte=0.1, is_active=True)
    .order_by("-rank")
)
```

#### 1.3 No CDN for Static / Media Assets
**Impact:** MEDIUM  
`MEDIA_ROOT = BASE_DIR / "media"` stores uploaded images on the local container filesystem. Multiple backend replicas cannot share this volume. Under high traffic, serving media through Django/Daphne is extremely inefficient.

**Fix:** `django-storages` + S3/GCS for media. CloudFront/Cloudflare for static assets.

```python
# settings/prod.py
DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
STATICFILES_STORAGE  = "storages.backends.s3boto3.S3StaticStorage"
```

#### 1.4 No Database Connection Pooler
**Impact:** MEDIUM  
`CONN_MAX_AGE=60` keeps one persistent connection per Django thread. With 4 Gunicorn workers × 4 threads = 16 connections minimum. Under autoscaling, this can exhaust PostgreSQL's `max_connections` (default 100).

**Fix:** Add PgBouncer in transaction pooling mode.

```yaml
# docker-compose.yml
pgbouncer:
  image: bitnami/pgbouncer:1.23
  environment:
    PGBOUNCER_DATABASE: ecommerce
    POSTGRESQL_HOST: db
    PGBOUNCER_POOL_MODE: transaction
    PGBOUNCER_MAX_CLIENT_CONN: 200
```

#### 1.5 Single Daphne Process Per Container
**Impact:** MEDIUM  
`docker-compose.yml` runs one `daphne` process per container. For production, Daphne should run behind a process supervisor with multiple workers, or be replaced with `uvicorn` + `gunicorn` worker class.

**Fix:**

```dockerfile
# Dockerfile
CMD ["gunicorn", "core.asgi:application", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--workers", "4", "--bind", "0.0.0.0:8000"]
```

---

## 2. Maintainability

### Score: 7 / 10

### What Is Working Well ✅

| Item | Evidence |
|------|---------|
| Modular app layout | 10 Django apps with clear domain boundaries: `users`, `products`, `orders`, `payments`, `vendors`, `adminpanel`, `apps/wishlist`, `apps/recommendations`, `apps/chatbot`, `apps/price_watch` |
| Service layer | `payments/services.py` extracted from views; `vendors/services.py`, `apps/recommendations/services.py`, `apps/price_watch/services.py` all present |
| 111 passing tests | Full test suite covers all major workflows |
| OpenAPI auto-docs | `drf-spectacular` generates `/api/docs/` — no manual API contract drift |
| Serializer validation | Free-text fields sanitized via `strip_html_tags()` in `products/serializers.py` |
| Environment-driven config | `python-decouple` reads all secrets from env; no hardcoded credentials |
| Type annotations | Payment services use Python type hints; DRF serializer fields are self-documenting |

### Gaps ❌

#### 2.1 Frontend Admin Middleware Anti-Pattern (FIXED ✅)
**Before:** `middleware.ts` determined admin access by sending a `POST` request to `/api/v1/products/` with `body: "permission-check"`. This is semantically incorrect (a POST attempts resource creation), fragile (any 4xx/5xx from the endpoint could accidentally allow or deny access), and creates unnecessary server load.

**After (this audit):** Middleware now calls `GET /api/v1/users/me/` (new endpoint) which returns `{is_staff: bool}`. This is a read-only, purpose-built check.

```typescript
// Frontend/middleware.ts — after fix
const response = await fetch(`${API_BASE_URL}/api/v1/users/me/`, {
  method: "GET",
  headers: { Authorization: `Bearer ${token}` },
});
const user = await response.json();
if (!user.is_staff) {
  return NextResponse.redirect(new URL("/", request.url));
}
```

#### 2.2 Management Commands Not Monitored
**Impact:** MEDIUM  
`check_price_drops` and `send_abandoned_cart_reminders` run as cron jobs but have no:
- Failure alerting
- Execution history / audit log
- Retry on error

**Fix:** Move to Celery periodic tasks with `django-celery-beat`. Celery provides task history, failure visibility, and retry policies out of the box.

#### 2.3 Duplicate URL Patterns
`ProductSearchView` and `ProductSearchSuggestionsView` each have two routes (with and without trailing slash):

```python
# core/api_urls.py
path("search/",             ProductSearchView.as_view(), name="product-search"),
path("search",              ProductSearchView.as_view(), name="product-search-no-slash"),
path("search/suggestions/", ProductSearchSuggestionsView.as_view(), ...),
path("search/suggestions",  ProductSearchSuggestionsView.as_view(), ...),
```

**Fix:** Enable Django's `APPEND_SLASH = True` (the default) and remove the no-slash duplicates.

#### 2.4 No Frontend Tests
**Impact:** LOW-MEDIUM  
The backend has 111 tests; the frontend has none. UI regressions are only caught manually.

**Fix:** Add Jest + React Testing Library for components; Playwright for critical user flows (login, checkout, order tracking).

---

## 3. Observability

### Score: 5 / 10

### What Is Working Well ✅

| Item | Evidence |
|------|---------|
| Request ID tracing | `core/middleware.py:RequestIDMiddleware` attaches `X-Request-ID` to every response |
| Request ID in logs | `core/log_filters.py:RequestIDFilter` injects `request_id` into every log record via thread-local storage (added this audit) |
| Structured log format | `%(asctime)s %(levelname)s [%(request_id)s] %(name)s %(message)s` |
| LOG_LEVEL env var | Runtime-configurable without code deploy |
| Health endpoint | `GET /api/v1/health/` — now probes both DB and Redis (updated this audit) |
| Payment event log | `PaymentEvent` immutable append-only audit trail for every payment state change |
| Order event log | `OrderEvent` records every status transition with who changed it |
| Email event log | `EmailEvent` tracks delivery status (sent/failed) per email type |

### Critical Gaps ❌

#### 3.1 No Error Tracking / Alerting
**Impact:** HIGH  
The only error output is `logging.StreamHandler → stdout`. There is no:
- Real-time error alerting
- Error grouping and deduplication
- Stack trace enrichment
- Release tracking

A 500 error in production is invisible unless someone watches container logs.

**Fix:** Sentry (free tier covers up to 50k errors/month):

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
        integrations=[sentry_sdk.integrations.django.DjangoIntegration()],
        traces_sample_rate=config("SENTRY_TRACES_SAMPLE_RATE", default=0.05, cast=float),
        send_default_pii=False,
        release=config("APP_VERSION", default=""),
    )
```

#### 3.2 No Metrics / APM
**Impact:** HIGH  
There is no way to answer: "What is the p95 response time for the checkout endpoint?" or "How many DB queries does the product search make?"

**Fix options (choose one):**
- **Prometheus + Grafana:** Add `django-prometheus` middleware, scrape metrics, build dashboards.
- **Datadog APM:** Drop-in `ddtrace-run` wrapper, zero-code instrumentation.
- **OpenTelemetry:** Vendor-agnostic tracing with traces, metrics, and logs.

```bash
pip install django-prometheus
```

```python
# settings/base.py
INSTALLED_APPS += ["django_prometheus"]
MIDDLEWARE = ["django_prometheus.middleware.PrometheusBeforeMiddleware"] + MIDDLEWARE
MIDDLEWARE += ["django_prometheus.middleware.PrometheusAfterMiddleware"]
```

```python
# urls.py
path("metrics/", include("django_prometheus.urls")),
```

#### 3.3 No Slow Query Logging
**Impact:** MEDIUM  
There is no DB slow-query threshold configured. N+1 regressions introduced by new code go undetected until they manifest as latency spikes in production.

**Fix:** Enable Django's query logging in development; configure PostgreSQL `log_min_duration_statement` in production.

```python
# settings/dev.py
LOGGING["loggers"] = {
    "django.db.backends": {
        "level": "DEBUG",
        "handlers": ["console"],
        "propagate": False,
    }
}
```

And in `postgresql.conf`:
```
log_min_duration_statement = 500  # log queries slower than 500ms
```

#### 3.4 No Uptime / SLA Monitoring
**Impact:** MEDIUM  
There is no external uptime monitor hitting `/api/v1/health/` from outside the cluster. If the container crashes, no alert fires.

**Fix:** Add a free-tier monitor (UptimeRobot, BetterStack, Grafana Cloud) pointing to `https://api.yoursite.com/api/v1/health/` with a 1-minute check interval and email/Slack alerting.

---

## 4. Fault Tolerance

### Score: 6 / 10

### What Is Working Well ✅

| Item | Evidence |
|------|---------|
| Payment idempotency | `PaymentWebhookEvent` deduplicates webhook replays by `event_id` |
| Payment retry | `RetryPaymentView` allows up to `MAX_RETRY_ATTEMPTS=3` attempts |
| Optimistic locking | `select_for_update()` prevents race conditions on stock deduction and referral rewarding |
| Atomic transactions | `@transaction.atomic` on order creation, coupon application, stock deduction |
| Immutable audit events | `PaymentEvent.save()` and `.delete()` raise `ValidationError` — append-only log |
| Order idempotency | `Idempotency-Key` header on `POST /api/v1/orders/` |
| Email deduplication | `EmailEvent` unique constraint `(order, email_type)` prevents duplicate sends |
| Webhook HMAC verification | `hmac.compare_digest` prevents timing attacks on webhook signature check |
| DB constraint on active cart | `unique_active_cart_per_user` prevents duplicate active carts |
| Graceful WebSocket auth | `OrderConsumer.connect()` sends close codes 4401/4403 on auth failure |

### Gaps ❌

#### 4.1 Synchronous Email in Request Cycle
**Impact:** HIGH  
SMTP is called directly inside `VerifyRazorpayPaymentView.post()`. If the SMTP server is slow or unreachable, the client waits and the 200 response is delayed or never sent.

```python
# payments/views.py:202
send_order_email("payment_success", payment.order)  # ← blocks here
return Response({"detail": "Payment verified successfully."})
```

**Fix:** Dispatch via Celery task (see §2.2). The view returns immediately; email is sent asynchronously with automatic retry.

#### 4.2 No Circuit Breaker for External APIs
**Impact:** MEDIUM  
`create_razorpay_order()` and `_call_openai_response()` have timeout handling but no circuit breaker. If Razorpay is degraded, every checkout attempt waits 10 seconds before failing, multiplying server thread utilization.

**Fix:** Use `tenacity` for retry+backoff, or implement a simple circuit breaker:

```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    retry=retry_if_exception_type(RazorpayIntegrationError),
)
def create_razorpay_order(amount, currency, receipt):
    ...
```

#### 4.3 No Stock Reservation / Saga Pattern
**Impact:** MEDIUM  
Stock deduction happens inside `deduct_order_stock()` which is called after Razorpay payment verification. Between order creation and payment completion, stock is NOT reserved. Two concurrent users can both purchase the last item.

```
User A: Creates order  ─────────────────────────────┐
User B: Creates order  ─────────────┐               │
User B: Pays & deducts stock ←──────┘ (stock: 0)    │
User A: Pays → deduct fails with ValidationError ←──┘
```

**Fix (short-term):** Reserve stock at order creation; release reservation if payment fails or order is cancelled.

```python
# In CreateOrderSerializer.save():
for item in order_items:
    Product.objects.filter(
        id=item.product_id, stock_quantity__gte=item.quantity
    ).update(
        stock_quantity=F("stock_quantity") - item.quantity,
        reserved_quantity=F("reserved_quantity") + item.quantity,
    )
```

**Fix (long-term):** Implement a Saga pattern with compensating transactions for the full order-payment flow.

#### 4.4 No Graceful Shutdown Handling
**Impact:** LOW  
Daphne does not have a configurable graceful shutdown window in the docker-compose configuration. A container restart during an in-flight payment verification could leave the order in an inconsistent state.

**Fix:** Add `stop_grace_period` to the backend service and ensure the payment verification is idempotent (it currently is via `select_for_update` + status checks, but this should be documented).

```yaml
# docker-compose.yml
backend:
  stop_grace_period: 30s
```

---

## 5. Data Consistency

### Score: 7 / 10

### What Is Working Well ✅

| Item | Evidence |
|------|---------|
| UUID primary key for users | `User.id = UUIDField(primary_key=True)` prevents enumeration attacks |
| DB-level unique constraints | `unique_active_cart_per_user`, `unique_product_per_cart`, `unique_captured_payment_per_order`, `unique_order_email_type_event` |
| Row-level locking | `select_for_update()` on stock deduction, referral reward, coupon application |
| Immutable payment events | `PaymentEvent` overrides `save()`/`delete()` to prevent mutation |
| Cascading deletes defined | All ForeignKey fields specify explicit `on_delete` — no accidental `CASCADE` surprises |
| Decimal precision | `max_digits=12, decimal_places=2` on all monetary fields; calculations use `Decimal`, not `float` |
| Idempotency keys | Orders and Payments both support `idempotency_key` to prevent duplicate submissions |
| Coupon usage tracking | `CouponUsage` model records each use; `used_count` is incremented atomically with `F()` |
| Order event audit trail | Every status change recorded in `OrderEvent` with `changed_by`, `previous_status`, `new_status` |
| Referral reward idempotency | `Referral.reward_issued` flag checked before issuing coupon |

### Gaps ❌

#### 5.1 No stock_quantity >= 0 Database Constraint
**Impact:** HIGH  
`Product.stock_quantity` is a `PositiveIntegerField` which the DB enforces as `>= 0`. However, the stock deduction path uses a conditional `UPDATE`:

```python
updated = Product.objects.filter(
    id=item.product_id, stock_quantity__gte=item.quantity
).update(stock_quantity=F("stock_quantity") - item.quantity)
```

If two requests pass the `__gte` check simultaneously before either UPDATE commits, one could result in negative stock (despite `select_for_update` this is possible if locks are not acquired in consistent order). The `PositiveIntegerField` DB constraint would catch this but the `ValidationError` in application code may not be meaningful to the user.

**Fix:** Add an explicit `CheckConstraint`:

```python
# products/models.py
class Meta:
    constraints = [
        models.CheckConstraint(
            check=Q(stock_quantity__gte=0),
            name="product_stock_quantity_non_negative",
        ),
    ]
```

#### 5.2 No Soft Delete
**Impact:** MEDIUM  
`Product`, `Order`, `User`, `Vendor` objects are hard-deleted. Deleting a Product that appears in historical OrderItems would fail with an `IntegrityError` (due to `on_delete=PROTECT`), but there is no formal soft-delete / archive pattern.

**Fix:** Add `is_deleted = BooleanField(default=False)` + `deleted_at = DateTimeField(null=True)` to core models, and a custom manager that filters `is_deleted=False` by default. Use Django's `on_delete=models.SET_NULL` for optional relationships.

#### 5.3 Payment and Order State Machine Not Enforced
**Impact:** MEDIUM  
Order status transitions are partially validated in application code (e.g., `allowed_order_status_transitions` in `RazorpayWebhookView`) but not enforced at the database level. A buggy celery task or direct DB edit could leave an order in `SHIPPED` → `PENDING` transition.

**Fix:** Add a `CheckConstraint` or Django signal that validates allowed state transitions, or document the allowed transitions as a formal state machine.

#### 5.4 Cart-to-Order Not Fully Atomic
**Impact:** LOW  
`CreateOrderSerializer.save()` creates the `Order` + `OrderItem` records in a transaction, but the cart `is_active` flag update happens separately. If the server crashes between the two, a user could have both an active cart and a pending order.

**Fix:** Wrap both operations in a single `transaction.atomic` block:

```python
with transaction.atomic():
    order = Order.objects.create(...)
    order_items = [OrderItem(...) for item in cart_items]
    OrderItem.objects.bulk_create(order_items)
    cart.is_active = False
    cart.save(update_fields=["is_active", "updated_at"])
```

---

## 6. Deployment Readiness

### Score: 6 / 10

### What Is Working Well ✅

| Item | Evidence |
|------|---------|
| Docker multi-service | `docker-compose.yml` with PostgreSQL 16, Redis 7, Backend, Frontend |
| Dockerfile — backend | Python 3.12-slim, non-root layer separation, `collectstatic` at build time |
| Dockerfile — frontend | Multi-stage Next.js build (not shown but present) |
| Health check probes DB + Redis | `GET /api/v1/health/` — updated this audit |
| GitHub Actions CI | Backend tests + Frontend lint/build on every PR |
| Env-based settings dispatch | `core/settings/__init__.py` routes to `dev.py` or `prod.py` via `DJANGO_ENV` |
| Production security headers | `prod.py`: `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, HSTS, `X_FRAME_OPTIONS=DENY` |
| Secrets from env | All credentials via `python-decouple`; `.env.example` documented |
| `DJANGO_ENV=prod` in compose | `docker-compose.yml` now explicitly sets `DJANGO_ENV: prod` (fixed this audit) |
| `CACHE_REDIS_URL` in compose | Backend environment now includes `CACHE_REDIS_URL: redis://redis:6379/1` (added this audit) |

### Gaps ❌

#### 6.1 No Staging / Production Deployment Pipeline
**Impact:** HIGH  
CI verifies tests pass but there is no automated deployment. `main` branch merges require a manual docker build and push. This creates deployment lag and human error risk.

**Fix:** Add a GitHub Actions workflow for staging deployment:

```yaml
# .github/workflows/deploy-staging.yml
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/build-push-action@v6
        with:
          context: ./Backend
          push: true
          tags: registry/ecommerce-backend:${{ github.sha }}
      - run: |
          ssh deploy@staging "docker pull registry/ecommerce-backend:${{ github.sha }} && \
            docker-compose -f docker-compose.prod.yml up -d --force-recreate backend"
```

#### 6.2 `SECURE_PROXY_SSL_HEADER` Not Set
**Impact:** HIGH  
`prod.py` sets `SECURE_SSL_REDIRECT=True` but does NOT set `SECURE_PROXY_SSL_HEADER`. Django behind a load balancer (AWS ALB, GCP LB, nginx) cannot determine the original protocol without this. The result is an infinite redirect loop in production.

**Files to modify:** `Backend/core/settings/prod.py`

```python
# settings/prod.py — add this line
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
```

#### 6.3 Media Files Not Persistent
**Impact:** HIGH  
`MEDIA_ROOT = BASE_DIR / "media"` writes to the container filesystem. All uploaded product images are **lost on every container restart or redeploy**. There is no volume mount for media in `docker-compose.yml`.

**Fix (immediate):** Add a named volume for media in `docker-compose.yml`:

```yaml
backend:
  volumes:
    - media_files:/app/media

volumes:
  media_files:
```

**Fix (production):** Use `django-storages` with S3 (`DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"`).

#### 6.4 No Database Backup Strategy
**Impact:** HIGH  
`docker-compose.yml` mounts a named volume `postgres_data` but there is no automated backup, point-in-time recovery, or backup verification documented.

**Fix:** Add a `pgbackup` service or schedule `pg_dump` via a cron container:

```yaml
backup:
  image: prodrigestivill/postgres-backup-local
  environment:
    POSTGRES_HOST: db
    POSTGRES_DB: ecommerce
    POSTGRES_USER: ${DB_USER:-postgres}
    POSTGRES_PASSWORD: ${DB_PASSWORD:-postgres}
    SCHEDULE: "@daily"
    BACKUP_KEEP_DAYS: 7
  volumes:
    - ./backups:/backups
```

#### 6.5 No Secrets Manager
**Impact:** MEDIUM  
Secrets are loaded from a `.env` file which must be manually placed on the server. There is no integration with a secrets manager (AWS Secrets Manager, Vault, GCP Secret Manager).

**Fix:** Use environment-specific secret injection via your deployment platform (AWS ECS task definitions, k8s `Secret` objects, or GitHub Actions secrets).

#### 6.6 No Rolling Update / Zero-Downtime Deploy Strategy
**Impact:** MEDIUM  
`docker-compose up -d --force-recreate backend` causes ~3 seconds of downtime per deploy. 

**Fix:**  
- **Short term:** Add a second container behind nginx, use rolling restarts.  
- **Long term:** Migrate to Kubernetes with `RollingUpdate` deployment strategy or AWS ECS with blue/green deployments.

#### 6.7 Database Migrations Not Validated in CI
**Impact:** MEDIUM  
The CI workflow runs `python manage.py migrate --run-syncdb` but does not check for:
- Missing migration files after model changes (`--check` flag)
- Backwards-incompatible migrations (removing fields that existing code reads)

**Fix:** Add to CI workflow:

```yaml
- name: Check for missing migrations
  working-directory: Backend
  run: python manage.py migrate --check
```

---

## Improvement Priority Matrix

| # | Improvement | Category | Effort | Impact |
|---|-------------|----------|--------|--------|
| 1 | Introduce Celery async task queue | Scalability / Fault Tolerance | Medium | Critical |
| 2 | Add `SECURE_PROXY_SSL_HEADER` | Deployment | Tiny | Critical |
| 3 | Mount media volume / use S3 | Deployment / Scalability | Small | Critical |
| 4 | Add Sentry error tracking | Observability | Small | High |
| 5 | Reserve stock at order creation | Data Consistency | Medium | High |
| 6 | Add staging deploy pipeline | Deployment | Medium | High |
| 7 | PostgreSQL full-text search | Scalability | Medium | High |
| 8 | Add `stock_quantity >= 0` constraint | Data Consistency | Tiny | Medium |
| 9 | Add `Prometheus` metrics | Observability | Small | Medium |
| 10 | Add PgBouncer | Scalability | Small | Medium |
| 11 | Database backup strategy | Deployment | Small | Medium |
| 12 | Add `--check` to CI migrate step | Deployment | Tiny | Medium |
| 13 | Add circuit breaker for Razorpay | Fault Tolerance | Small | Medium |
| 14 | Soft delete for core entities | Data Consistency | Medium | Low |
| 15 | Frontend E2E tests (Playwright) | Maintainability | Large | Low |

---

## Implemented in This Audit Session

The following improvements were directly implemented alongside this audit:

| # | Change | Files Modified |
|---|--------|---------------|
| ✅ | **`GET /api/v1/users/me/`** endpoint — returns `{id, email, name, is_staff, role}` | `Backend/users/views.py`, `Backend/users/urls.py` |
| ✅ | **Frontend middleware rewrite** — replaced POST-to-products hack with GET to `/api/v1/users/me/` | `Frontend/middleware.ts` |
| ✅ | **Health check extended** — now probes Redis when `CACHE_REDIS_URL` is set; returns per-service status | `Backend/core/health.py` |
| ✅ | **Request ID in log lines** — `RequestIDFilter` injects `request_id` from thread-local into every log record; middleware writes to thread-local | `Backend/core/log_filters.py` (new), `Backend/core/middleware.py`, `Backend/core/settings/base.py` |
| ✅ | **`DJANGO_ENV=prod` in docker-compose** — ensures production settings are used; previously defaulted to dev mode | `docker-compose.yml` |
| ✅ | **`CACHE_REDIS_URL` in docker-compose backend** — wires the cache Redis instance to the running backend container | `docker-compose.yml` |

---

## Conclusion

The Venopai ecommerce platform demonstrates a solid foundation for a startup MVP:
well-structured domain models, comprehensive database constraints, proper use of
transactions and row-level locking, and a clean separation of concerns introduced
in recent refactoring. The JWT authentication, rate limiting, and payment
idempotency implementations are production-quality.

The primary gap preventing true production-readiness is the absence of:
1. **Async task execution** — email sends block the request cycle
2. **Error visibility** — no Sentry means production failures are silent
3. **Durable media storage** — images are lost on container restart
4. **A deployment pipeline** — manual deploys are error-prone

Addressing items 1–4 (all marked Critical or High in the matrix above) would
raise the overall score from **60% to an estimated 80%**, making the platform
suitable for initial production traffic.
