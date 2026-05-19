# Production Go/No-Go Checklist

## Go criteria
- [ ] CI green for backend and frontend.
- [ ] Migrations reviewed with rollback plan.
- [ ] Staging validation checklist complete.
- [ ] Smoke test passes in production.
- [ ] Load test results within targets.
- [ ] On-call and incident contacts confirmed.
- [ ] Backup within last 24 hours.

## No-Go criteria
- [ ] Known checkout or payment failures unresolved.
- [ ] Reservation cleanup task not running.
- [ ] Sentry or metrics unavailable.
- [ ] Deployment rollback plan missing.
- [ ] DB latency or error rate above baseline.

## Decision
- Decision owner: ____________________
- Decision time: _____________________
- Go / No-Go: ________________________
