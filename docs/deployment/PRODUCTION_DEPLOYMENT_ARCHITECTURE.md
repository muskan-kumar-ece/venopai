# Production Deployment Architecture

## Service Topology

- `frontend` (Next.js)
- `backend` (Django ASGI + Daphne)
- `worker` (Celery worker)
- `scheduler` (Celery beat)
- `postgres` (primary relational store)
- `redis` (cache, broker, channel layer)

## Compose Files

- `docker-compose.dev.yml`: local development stack
- `docker-compose.prod.yml`: production-like deployment stack

## Environment Layers

- Shared infra (production only):
  - `./.env.production` (postgres + shared DB values, not committed)
- Backend templates:
  - `Backend/.env.example`
  - `Backend/.env.local` (developer-local, not committed)
  - `Backend/.env.production.example`
- Frontend templates:
  - `Frontend/.env.example`
  - `Frontend/.env.local` (developer-local, not committed)
  - `Frontend/.env.production.example`

## Async Workflows

- Abandoned cart reminders
- Reservation cleanup
- Pending payment reconciliation
- Webhook retry processing (dead-letter after retry ceiling)
- Analytics cache aggregation
- Order/payment/refund email delivery

## Startup Validation

- `python manage.py validate_startup`
- Used by `docker-compose.prod.yml` backend startup command

## CI/CD Workflows

- Backend quality/lint/test/migration checks: `.github/workflows/backend-ci.yml`
- Frontend lint/typecheck/build: `.github/workflows/frontend-ci.yml`
- Deploy examples:
  - `.github/workflows/deploy-staging-example.yml`
  - `.github/workflows/deploy-production-example.yml`
