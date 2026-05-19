# Load Test Guidance

## Objectives

- Validate checkout + payment verification stability under moderate concurrency.
- Validate reservation cleanup and webhook replay behavior under retry pressure.
- Validate auth refresh and login throttle behavior.

## Recommended Tooling

- `k6` for HTTP-level flow tests.
- `locust` for scenario-based user sessions.

## Critical Scenarios

1. Catalog Browsing
- `GET /api/v1/products/`
- `GET /api/v1/products/home-catalog/`
- Target: cache hit ratio and p95 latency.

2. Checkout Lifecycle
- add-to-cart -> checkout-from-cart -> verify payment.
- Measure conflicts, reservation failures, idempotency collisions.

3. Webhook Replay
- replay same webhook payload and event ID.
- Verify idempotent accept path and retry queue behavior.

4. Auth Pressure
- repeated token refresh with mixed valid/expired refresh tokens.
- repeated invalid login attempts to verify lockout.

## Suggested Targets (Moderate Launch)

- API p95 < 400ms for cached reads.
- Checkout success > 98% without stock contention.
- Webhook processing success > 99.9% with replay safety.
- Background task failure rate < 1% with retries.

## Runbook Checks During Load

- `/api/v1/health/`
- `/api/v1/observability/metrics/`
- Celery worker logs + dead-letter webhook records.
- DB connection saturation and slow queries.

## Scripted Scenarios

Load test scripts live under `load_tests/`:

- `k6_checkout.js` — concurrent checkout lifecycle.
- `k6_inventory_contention.js` — stock contention and reservation pressure.
- `k6_webhook_burst.js` — webhook burst and replay safety.
- `k6_auth_refresh.js` — refresh token storms.

Common environment variables:
- `BASE_URL` (default: `http://localhost:8000/api/v1`)
- `AUTH_EMAIL` / `AUTH_PASSWORD`
- `AUTH_EMAILS` (comma-separated pool for VUs)
- `PRODUCT_ID` (optional override for checkout and contention)
- `RAZORPAY_WEBHOOK_SECRET` (webhook script)
- `RAZORPAY_ORDER_ID` (webhook script, optional)
