# AI Context (Consolidated)

## Purpose
This document provides structured context for AI coding assistants to generate consistent, production-grade code for Venopai.

## Project Overview
Venopai is a student-focused ecommerce and custom manufacturing platform with:
- Standard ecommerce products
- Custom printing/manufacturing requests
- Admin-controlled fulfillment
- Razorpay payments with webhook verification

## Tech Stack (Required)
Frontend:
- Next.js (App Router)
- TypeScript
- Tailwind CSS
- Axios (centralized API client)

Backend:
- Django + Django REST Framework
- PostgreSQL
- Celery + Redis

Storage:
- Cloudinary (media uploads)

Payments:
- Razorpay (server-side verification)

## Backend Architecture Rules
- Each feature is a separate Django app.
- Business logic must live in services, not views.
- Use serializers for validation.
- Use atomic transactions for payments and order creation.
- JWT authentication for protected endpoints.

## Frontend Architecture Rules
- Use App Router and TypeScript.
- Centralize API calls (axios instance).
- Use typed responses and hooks for data access.
- Avoid inline styles; follow design system.

## API Response Standard
Success:
{
  "success": true,
  "data": {},
  "message": "Action successful"
}

Error:
{
  "success": false,
  "error": "Error message"
}

## Security Rules
- Never hardcode secrets.
- Always validate Razorpay webhooks server-side.
- Sanitize inputs and validate file uploads.

## Performance Rules
- Use select_related / prefetch_related.
- Paginate large queries.
- Use caching for heavy reads.

## AI Behavior Expectations
- Follow existing architecture and naming conventions.
- Avoid unnecessary complexity or new frameworks.
- If uncertain, ask for clarification.

## Reference Documents
- product/VENOPAI_PRD.md
- product/VENOPAI_TRD.md
- reference/VENOPAI_DATABASE_SCHEMA.md
- product/VENOPAI_PRODUCT_BLUEPRINT.md
- product/DESIGN_SYSTEM.md
