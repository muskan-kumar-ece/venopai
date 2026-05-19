# Staging Environment Validation Checklist

## Configuration parity
- [ ] Staging env vars match production defaults (except domains and secrets).
- [ ] `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET` set for test mode.
- [ ] `SENTRY_DSN` configured with staging environment tag.
- [ ] `CACHE_REDIS_URL`, `CELERY_BROKER_URL`, `CHANNEL_REDIS_URL` wired.
- [ ] `INVENTORY_RESERVATION_TTL_MINUTES` set (default 15).

## Redis persistence
- [ ] AOF enabled (`appendfsync everysec`) or managed persistence on.
- [ ] Redis reboot preserves critical queues.
- [ ] Celery broker reconnects cleanly after Redis restart.

## Celery retries
- [ ] Task retries are visible in logs for forced failures.
- [ ] `cleanup_stale_checkout_sessions_task` runs on schedule.
- [ ] Webhook retry queue shows expected behavior.

## Observability
- [ ] Sentry events captured from both backend and frontend.
- [ ] `/api/v1/observability/metrics/` accessible by admin.
- [ ] Alerts configured for checkout and payment failure spikes.

## Payments and webhooks
- [ ] Checkout-from-cart creates reservations and payment sessions.
- [ ] Payment verification updates order/payment statuses.
- [ ] Webhook replay returns 200 and does not double-deduct stock.

## Rollback readiness
- [ ] Migration rollback plan verified in staging.
- [ ] Last release image available and deployable.
- [ ] Rollback smoke test passes.

## Staging signoff
- [ ] Smoke tests complete.
- [ ] Load tests meet targets.
- [ ] Release checklist ready to execute.
