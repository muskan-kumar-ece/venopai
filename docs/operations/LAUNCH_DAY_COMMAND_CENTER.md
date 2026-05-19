# Launch Day Command Center Checklist

## Roles
- Incident lead (decision maker)
- Ops owner (deploy/rollback)
- Payments owner (webhooks and verification)
- Inventory owner (reservations and stock)
- Support liaison (customer communication)

## Live monitors
- API error rate and latency dashboards
- Checkout conversion rate
- Payment verification failure alerts
- Webhook retry queue depth
- Reservation cleanup task health
- Redis and DB saturation

## Timeline
1. T minus 60: confirm readiness and freeze changes.
2. T minus 30: run smoke test in production.
3. T minus 10: enable checkout and payment flags.
4. T plus 30: review conversion and error rates.
5. T plus 60: first post-launch summary.

## Escalation triggers
- 5xx rate > 2 percent for 5 minutes.
- Payment verification failures > 5 in 10 minutes.
- Reservation cleanup failures > 3 in 15 minutes.
- Webhook retries > 50 for 10 minutes.

## Comms plan
- Use a single incident channel for status.
- Update stakeholders every 30 minutes during instability.
- Customer updates only for Sev0/Sev1 incidents.
