# Launch Validation Checklist

## Pre-launch validation
- [ ] All integration tests passing.
- [ ] Smoke test passes on staging.
- [ ] Load test results reviewed (checkout, contention, webhook, auth refresh).
- [ ] Backup restore drill executed in staging.
- [ ] Deployment rollback drill executed in staging.

## Production readiness validation
- [ ] Sentry DSN and alert rules enabled.
- [ ] Metrics dashboard shows normal baseline.
- [ ] Reservation cleanup task visible and healthy.
- [ ] Webhook retry queue in normal range.
- [ ] Inventory audit logs being created for reserve/release/finalize.

## Launch day readiness
- [ ] Command center checklist ready.
- [ ] Go/No-Go checklist reviewed.
- [ ] Incident response contacts confirmed.
