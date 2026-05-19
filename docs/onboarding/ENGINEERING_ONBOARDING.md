# Engineering Onboarding

## Purpose
This guide helps new engineers ramp up quickly with Venopai's architecture, environments, and operating procedures.

## Quick Start
1. Read docs/README.md for the documentation map.
2. Set up local environment using docs/onboarding/ENVIRONMENT_SETUP.md.
3. Review reference/API_CONTRACT.md for API expectations.
4. Review architecture/CART_ARCHITECTURE_ANALYSIS.md for cart and checkout flows.
5. Run backend and frontend via docker-compose.dev.yml.

## Repository Orientation
- Backend/ : Django backend services (orders, payments, products, users, adminpanel).
- Frontend/ : Next.js app (App Router, components, lib).
- docs/ : Operational, security, and architecture documentation.
- load_tests/ : k6 and Locust load scenarios.
- scripts/ : Smoke test automation.

## Key Systems to Understand
- Cart and checkout lifecycle (server cart + inventory reservation).
- Payments (Razorpay order creation, webhook verification, idempotency).
- Async processing (Celery workers, scheduler, Redis broker).
- Observability (Sentry + operational alerting).

## Local Development Flow
- Backend: docker-compose.dev.yml runs backend, postgres, redis, worker, scheduler.
- Frontend: docker-compose.dev.yml runs Next.js with local env.
- Smoke tests: scripts/smoke_test.py (see testing/TESTING_STRATEGY.md).

## Required Reading for Production Work
- operations/OPERATIONS_INDEX.md
- deployment/DEPLOYMENT_OVERVIEW.md
- security/SECURITY_OVERVIEW.md

## Contribution Expectations
- Follow API response formats in reference/API_CONTRACT.md.
- Keep operational behavior aligned with runbooks in operations/.
- Update docs when introducing new config or workflow changes.
