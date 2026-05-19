# Release Checklist and Smoke Tests

## Pre-release checklist (T minus 1 to 3 days)
- CI green for backend and frontend.
- Migrations reviewed with rollback plan.
- Feature flags documented and default values set.
- Backups verified within last 24 hours.
- Release notes drafted.

## Release checklist (day of deploy)
- Freeze changes and announce window.
- Confirm current error rate baseline.
- Apply migrations in staging and run smoke tests.
- Deploy to production.
- Verify:
  - Migration checks
  - Checkout flow
  - Payment verification and webhook
  - Reservation cleanup job
  - Auth login and refresh

## Post-release checklist (first 2 hours)
- Monitor error rate and latency.
- Check payment success rate.
- Confirm order creation and inventory updates.
- Verify Celery queue health.
- Review Sentry and logs for new errors.

## Smoke test flow
1. Log in as a normal user.
2. Browse products and add to cart.
3. Start checkout and validate stock.
4. Complete payment in test mode.
5. Verify order status transitions to paid.
6. Confirm webhook event recorded.
7. Confirm reservation cleanup task runs (staging).
8. Log out and refresh token flow.

## Canary deployment guidance
- Stage 1: internal traffic only (engineering).
- Stage 2: 10 percent of traffic for 30 minutes.
- Stage 3: 50 percent for 60 minutes.
- Stage 4: 100 percent.

Abort criteria:
- Error rate > 2 percent for 5 minutes.
- Payment success rate drop > 5 percent.
- p95 latency > 2x baseline for 10 minutes.
