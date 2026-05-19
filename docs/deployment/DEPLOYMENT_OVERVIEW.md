# Deployment Overview

## Service Topology
- frontend (Next.js)
- backend (Django ASGI + Daphne)
- worker (Celery worker)
- scheduler (Celery beat)
- postgres (primary relational store)
- redis (cache, broker, channel layer)

## Compose Files
- docker-compose.dev.yml : local development stack
- docker-compose.prod.yml : production-like deployment stack
- docker-compose.yml : baseline stack (prod defaults)

## Deployment Flow (High Level)
1. Build and tag backend and frontend images.
2. Apply database migrations.
3. Deploy backend, worker, scheduler, and frontend services.
4. Validate startup and health endpoints.
5. Run smoke tests and observe metrics.

## Environment Inputs
- ./.env.production (shared infra for postgres)
- Backend/.env.production (backend runtime)
- Frontend/.env.production (frontend runtime)

For local development, use Backend/.env.local and Frontend/.env.local.

## Runbooks
See deployment/PRODUCTION_DEPLOYMENT_RUNBOOKS.md for detailed steps and rollback guidance.
