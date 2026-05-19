# Production Hardening Checklist

## Performance

- [ ] Enable Redis cache (`CACHE_REDIS_URL`) in staging and production.
- [ ] Validate product/category/home catalog cache hit rates.
- [ ] Confirm compression enabled (`GZipMiddleware`, frontend compression).
- [ ] Confirm pagination limits and payload sizes for order/product endpoints.
- [ ] Review SQL query counts for cart, checkout, order detail, admin dashboard.

## Security

- [ ] Configure strong `SECRET_KEY` (>=32 chars).
- [ ] Set explicit `ALLOWED_HOSTS`.
- [ ] Set `ADMIN_URL_PATH` to non-default value.
- [ ] Verify secure cookie flags and SameSite policy.
- [ ] Verify CSP, HSTS, X-Frame-Options, Referrer-Policy headers.
- [ ] Verify webhook signature enforcement remains strict.
- [ ] Verify login brute-force lockout behavior.

## Async Reliability

- [ ] Worker and beat both healthy.
- [ ] Retry queues monitored (`PaymentWebhookRetry` dead-letter count).
- [ ] Reservation cleanup periodic task running.
- [ ] Payment reconciliation task running.

## Database/Indexes

- [ ] Run migrations for:
  - `orders` reservation/payment status composite index
  - `payments` webhook event indexes
  - `users` auth-event request-id index
- [ ] Confirm query plans use expected indexes in staging.

## Observability

- [ ] Sentry DSN configured backend + frontend.
- [ ] Alerts configured for:
  - checkout failures
  - payment verify failures
  - webhook retry dead letters
  - auth refresh/login lockout anomalies

## Validation Gates

- [ ] `python manage.py validate_startup`
- [ ] CI green: lint, typecheck, tests, build, migration checks.
- [ ] Smoke test: login, browse, checkout, verify payment, webhook replay.
