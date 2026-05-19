# Ecommerce Platform – Full Technical Audit Report

**Date:** March 2026  
**Audited by:** Automated architecture review  
**Repository:** `muskan-kumar-ece/Ecommerce`

---

## SECTION 1 – Current System Overview

### Architecture Pattern
The project is a **modular monolith** split into two separate deployment units:

| Tier | Technology | Notes |
|------|-----------|-------|
| **Backend** | Django 5.2 + Django REST Framework | ASGI via Daphne; WebSockets via Django Channels |
| **Frontend** | Next.js 14 (App Router) + TypeScript | React 18, Tailwind CSS, Zustand, React Query |
| **Database** | PostgreSQL (primary) / SQLite (dev) | psycopg2-binary adapter |
| **Cache / Pubsub** | Redis | Django Channels channel layer |
| **Auth** | JWT (SimpleJWT) | Rotate-on-refresh, blacklist on rotation |
| **Payments** | Razorpay | Create order → verify signature → webhook |

### Project Folder Structure

```
Ecommerce/
├── Backend/
│   ├── core/                   # Settings, URL routing, ASGI/WSGI config
│   │   ├── settings/
│   │   │   ├── base.py         # Shared settings (JWT, DRF, email, logging)
│   │   │   ├── dev.py          # DEBUG=True, inherits base
│   │   │   └── prod.py         # DEBUG=False, HTTPS security headers
│   │   ├── api_urls.py         # All /api/v1/ routes
│   │   ├── urls.py             # Root URL conf (admin, api/v1/, adminpanel)
│   │   ├── routing.py          # WebSocket routing
│   │   ├── asgi.py             # ASGI entrypoint
│   │   └── wsgi.py             # WSGI fallback
│   ├── users/                  # Auth, profiles, referral system
│   ├── products/               # Catalog, inventory, flash sales, reviews
│   ├── orders/                 # Cart, orders, coupons, shipping, analytics
│   ├── payments/               # Razorpay integration, webhooks, events
│   ├── vendors/                # Multi-vendor support, earnings
│   ├── adminpanel/             # Order management views for staff
│   └── apps/
│       ├── chatbot/            # OpenAI-powered chatbot
│       ├── wishlist/           # Saved products
│       ├── price_watch/        # Price drop alerts
│       └── recommendations/    # Collaborative filtering service
├── Frontend/
│   ├── app/                    # Next.js App Router pages
│   │   ├── (store)/            # Customer-facing pages
│   │   ├── (auth)/             # Login / Register
│   │   └── (admin)/dashboard/  # Admin analytics dashboard
│   ├── components/             # Shared React components
│   ├── lib/
│   │   ├── api/                # Axios API modules per domain
│   │   └── stores/             # Zustand auth store
│   └── public/                 # Static assets
├── docs/                       # Design docs, PRD, API contract
├── .github/workflows/          # CI/CD (GitHub Actions)
├── docker-compose.yml          # Multi-service container orchestration
└── API_CONTRACT.md             # Public API specification
```

### Missing Architectural Layers (identified)
- No dedicated task queue / worker (Celery / RQ) – management commands run manually
- No object storage for media files (S3/GCS) – uses local `MEDIA_ROOT`
- No CDN layer for static assets
- No distributed tracing (OpenTelemetry / Sentry)

---

## SECTION 2 – Implemented Features

### User & Auth
| Feature | How It Works |
|---------|-------------|
| Registration | `POST /api/v1/users/register/` – `RegisterUserSerializer` creates user; optional `referral_code` triggers `Referral` record |
| Login | `POST /api/v1/auth/token/` – SimpleJWT issues access + refresh JWT pair |
| Token refresh | `POST /api/v1/auth/token/refresh/` – rotates token, blacklists old refresh token |
| Referral system | Unique code per user; `Referral` model tracks referrer→referred; coupon issued on first paid order |

### Product Catalog
| Feature | How It Works |
|---------|-------------|
| Listing | `GET /api/v1/products/` – paginated (20/page), supports `search`, `category`, `in_stock`, `min_price`, `max_price`, `ordering` |
| Detail | `GET /api/v1/products/{id}/` – full product with images, inventory, avg rating |
| Search | `GET /api/v1/search/` – trigram + icontains relevance scoring; suggestions at `/search/suggestions/` |
| Flash sales | `GET /api/v1/flash-sales/` – time-gated discounts with countdown and stock limit |
| Reviews | `POST /api/v1/reviews/` – verified-purchase gate; rating 1–5 |
| Inventory | `Inventory` model tracks quantity, reserved, reorder level |
| Categories | `CategoryViewSet` – full CRUD |

### Shopping & Orders
| Feature | How It Works |
|---------|-------------|
| Cart | `CartViewSet` + `CartItemViewSet` – per-user, active/inactive states |
| Checkout | `POST /api/v1/orders/` – converts active cart to `Order` |
| Coupon codes | `POST /api/v1/orders/{id}/apply-coupon/` – validates limits, applies discount |
| Order tracking | `GET /api/v1/orders/{id}/` – status + `OrderEvent` log |
| Shipping events | `ShippingEvent` model records each logistics milestone |
| Abandoned cart | `send_abandoned_cart_reminders` management command sends email after 24 h |
| Real-time updates | Django Channels WebSocket consumer streams order status changes |

### Payments
| Feature | How It Works |
|---------|-------------|
| Create Razorpay order | `POST /api/v1/payments/create-order/` |
| Verify payment | `POST /api/v1/payments/verify/` – HMAC-SHA256 signature check |
| Retry | `POST /api/v1/payments/retry/` – up to 3 attempts |
| Refund | `POST /api/v1/payments/refund/` – calls Razorpay Refund API |
| Webhook | `POST /api/v1/payments/webhook/` – idempotent, deduped via `PaymentWebhookEvent` |

### Vendor Marketplace
| Feature | How It Works |
|---------|-------------|
| Vendor profile | `GET/POST /api/v1/vendors/profile/` |
| Vendor products | `GET /api/v1/vendors/dashboard/products/` |
| Vendor orders | `GET /api/v1/vendors/dashboard/orders/` |
| Earnings | `GET /api/v1/vendors/dashboard/earnings/` – aggregated via `VendorOrder` |

### Admin Features
| Feature | How It Works |
|---------|-------------|
| Analytics | `GET /api/v1/admin/analytics/` – revenue, orders, referrals, daily metrics (IsAdminUser) |
| Order management | `/admin/orders/` – list, detail, status update, ship, deliver |
| Analytics summary | `GET /admin/analytics/summary/` |
| Django Admin | `/admin/` – full model-level CRUD |

### Wishlist, Price Watch, Chatbot, Recommendations
| Feature | How It Works |
|---------|-------------|
| Wishlist | `GET/POST /api/v1/wishlist/`, `DELETE /api/v1/wishlist/{product_id}/` |
| Price watch | Users subscribe to price; `check_price_drops` command sends alerts |
| Chatbot | `POST /api/v1/chatbot/` – OpenAI-powered; handles product queries + order status |
| Recommendations | `apps.recommendations.services` – collaborative filtering returning top-10 |

---

## SECTION 3 – Architecture Issues

### 3.1 No Task Queue
- Management commands (`send_abandoned_cart_reminders`, `check_price_drops`) run synchronously and must be scheduled externally (cron / Celery beat).
- Webhook payment processing and email sends happen inside the HTTP request cycle – any delay blocks the response.
- **Fix:** Introduce Celery + Redis broker; move email sends and price-check to tasks.

### 3.2 No Caching Layer
- Product listings, search results, and analytics queries hit the database on every request.
- No Django cache backend is configured.
- **Fix:** Configure `django.core.cache` with Redis (`django-redis`) and apply `@cache_page` / `cache.get/set` to read-heavy endpoints.

### 3.3 No Object Storage
- `MEDIA_ROOT` writes uploaded files to local disk, which is not shared between containers and lost on redeploy.
- **Fix:** Use `django-storages` with S3 or GCS for `DEFAULT_FILE_STORAGE`.

### 3.4 Monolithic URL Namespacing
- Admin API routes (`/admin/orders/`) live in root `urls.py` outside the versioned `/api/v1/` prefix, making them inconsistent.

### 3.5 No API Versioning Strategy
- All endpoints are `/api/v1/` but there is no documented deprecation policy or v2 migration path.

---

## SECTION 4 – Security Issues

### 4.1 Brute-Force on Auth Endpoints – FIXED ✅
- **Before:** Login (`/auth/token/`) had no throttle; unlimited attempts possible.
- **After:** `AuthTokenThrottle` (`scope=auth`, default 10/minute) added to both token endpoints.

### 4.2 Missing Global Rate Limiting – FIXED ✅
- **Before:** No `DEFAULT_THROTTLE_CLASSES` in `REST_FRAMEWORK`.
- **After:** `AnonRateThrottle` (100/hour) and `UserRateThrottle` (2000/hour) configured globally; all values overridable via environment variables.

### 4.3 Webhook Signature Verification
- Razorpay webhook is verified with HMAC-SHA256 – correctly implemented in `payments/views.py`.

### 4.4 Payment Idempotency
- `PaymentWebhookEvent` deduplicates webhook replays – correctly implemented.

### 4.5 Password Storage
- Uses Django's default PBKDF2-SHA256 with `AUTH_PASSWORD_VALIDATORS` for strength checks – acceptable.

### 4.6 CSRF
- CSRF middleware enabled; `CSRF_TRUSTED_ORIGINS` is configurable. API endpoints use JWT (not session auth) so CSRF is not applicable to API routes.

### 4.7 CORS
- `CORS_ALLOWED_ORIGINS` is configurable and defaults to `http://localhost:3000` – must be set correctly in production.

### 4.8 Secret Management
- `SECRET_KEY`, database credentials, and payment secrets are loaded via `python-decouple` – no hardcoded secrets found.

### 4.9 Webhook Endpoint Authentication
- `RazorpayWebhookView` uses `AllowAny` permission class; security relies entirely on HMAC signature verification. This is the correct pattern for webhooks.

### 4.10 Missing Input Sanitization
- DRF serializers provide type validation but no explicit HTML/script sanitization on free-text fields (product description, review text). Consider adding a sanitizer for XSS prevention in stored content.

---

## SECTION 5 – Performance Problems

### 5.1 N+1 Queries
- `CartViewSet.get_queryset()` uses `prefetch_related("items")` – good.
- `CartItemViewSet.get_queryset()` uses `select_related("cart", "product")` – good.
- `OrderViewSet` – review `items` + `shipping_address` prefetch coverage for detail endpoints.
- Admin analytics uses aggregated DB queries, not Python loops – good.

### 5.2 No Caching
- Every product listing and search hits the DB. Under load, this will be the primary bottleneck.

### 5.3 Product Search
- Uses Django ORM `icontains` (LIKE queries) + manual relevance scoring in Python. This will degrade at scale.
- **Fix:** Migrate to PostgreSQL full-text search (`SearchVector`/`SearchQuery`) or Elasticsearch.

### 5.4 Large Payloads
- `ProductSerializer` returns full nested objects (images, inventory, category). The list endpoint may return excessive data.
- Consider a lightweight list serializer vs a detailed serializer.

### 5.5 Synchronous Email Sends
- `send_order_email()` is called synchronously inside request handlers. SMTP timeouts will block the response.

### 5.6 Database Connection Pooling
- `CONN_MAX_AGE=60` is configured (persistent connections) – good baseline.
- For high concurrency, consider PgBouncer or `django-db-connection-pool`.

---

## SECTION 6 – Code Quality Problems

### 6.1 Duplicate URL Patterns
- `ProductSearchView` and `ProductSearchSuggestionsView` each have two routes (with and without trailing slash). Consider using `APPEND_SLASH=True` (Django default).

### 6.2 Large `payments/views.py`
- File mixes business logic (stock deduction, referral issuing, coupon creation) with HTTP handling. Extract to a `payments/services.py` module.

### 6.3 Inline Business Logic in Views
- `_deduct_order_stock`, `_issue_referral_reward`, `_create_vendor_order` are module-level functions in `payments/views.py` alongside HTTP view classes – move to a service/domain layer.

### 6.4 Management Commands as Background Jobs
- `check_price_drops` and `send_abandoned_cart_reminders` work correctly but require external cron scheduling and cannot be monitored or retried.

### 6.5 Missing Error Handling in Chatbot
- OpenAI API calls should catch `openai.RateLimitError`, `openai.APIConnectionError`, etc., separately and return meaningful errors to the client.

### 6.6 No API Documentation Auto-Generation
- No `drf-spectacular` or `drf-yasg` integration. The `API_CONTRACT.md` is manually maintained and can drift from the implementation.

---

## SECTION 7 – Production Readiness Score

| Category | Score | Reasoning |
|----------|-------|-----------|
| **Feature Completeness** | 90/100 | All core e-commerce flows implemented; minor gaps in admin UX |
| **Security** | 70/100 | Rate limiting added; no input sanitization; no MFA |
| **Performance** | 55/100 | No caching; sync email; LIKE-based search |
| **Observability** | 40/100 | Console logging only; no Sentry/OpenTelemetry; no health endpoint |
| **Reliability** | 50/100 | No task queue; email/stock deduction in request cycle |
| **Scalability** | 45/100 | No CDN; no object storage; no caching; no connection pooler |
| **Testing** | 75/100 | 111 passing tests; good coverage; no frontend tests |
| **CI/CD** | 60/100 | GitHub Actions added; no deployment pipeline yet |
| **Containerization** | 70/100 | Dockerfiles and docker-compose added |
| **Documentation** | 65/100 | API contract exists; no OpenAPI spec |

### **Overall Production Readiness: 62/100**

The platform is feature-complete for an MVP but requires infrastructure hardening before production traffic.

---

## SECTION 8 – Priority Fix Roadmap

### P0 – Critical (do before launch)

| # | Task | Effort |
|---|------|--------|
| 1 | ~~Add API rate limiting (auth brute-force protection)~~ **DONE** | Small |
| 2 | ~~Create CI/CD GitHub Actions pipelines~~ **DONE** | Small |
| 3 | ~~Add Dockerfiles + docker-compose~~ **DONE** | Small |
| 4 | Configure `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `SECRET_KEY` from secrets manager in production | Small |
| 5 | Enable PostgreSQL full-text search or add Elasticsearch for product search | Medium |
| 6 | Move email sends to async task queue (Celery + Redis) | Medium |

### P1 – High (within 2 sprints)

| # | Task | Effort |
|---|------|--------|
| 7 | Add Redis caching for product listings, search results, and analytics | Medium |
| 8 | Configure `django-storages` with S3/GCS for media file uploads | Small |
| 9 | Integrate Sentry (or OpenTelemetry) for error tracking and distributed tracing | Small |
| 10 | Add `/api/v1/health/` endpoint for load-balancer health checks | Small |
| 11 | Add `drf-spectacular` for auto-generated OpenAPI docs | Small |
| 12 | Add HTML sanitization on free-text input fields (XSS prevention) | Small |

### P2 – Medium (next quarter)

| # | Task | Effort |
|---|------|--------|
| 13 | Add PgBouncer or connection pooler for high-concurrency DB access | Medium |
| 14 | Extract business logic from `payments/views.py` into `payments/services.py` | Medium |
| 15 | Add frontend unit/integration tests (Jest + React Testing Library) | Large |
| 16 | Set up staging environment with automated deployment on merge to `main` | Medium |
| 17 | Implement Admin 2FA / MFA | Medium |
| 18 | Add a dedicated API versioning strategy (v2 migration policy) | Small |

### P3 – Nice to Have

| # | Task | Effort |
|---|------|--------|
| 19 | CDN (CloudFront / Cloudflare) for static assets and media | Small |
| 20 | Add GraphQL or BFF (Backend-for-Frontend) layer for mobile clients | Large |
| 21 | Celery beat for scheduled price-drop and abandoned-cart jobs | Small |
| 22 | Real-time inventory push via WebSocket on product pages | Medium |
