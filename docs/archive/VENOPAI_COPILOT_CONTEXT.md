VENOPAI_COPILOT_CONTEXT.md

Purpose

This document provides structured context for AI coding assistants (GitHub Copilot, ChatGPT, etc.) to generate consistent, production-grade code for Venopai.

AI must follow this document strictly when generating backend or frontend code.


---

1. Project Overview

Venopai is a student-focused ecommerce and custom manufacturing platform.

Core Capabilities:

Standard product ecommerce (T-shirts, merchandise)

Custom printing service

Student project manufacturing requests

Admin-controlled fulfillment system

Razorpay payment integration


Primary Users:

Students (customers)

Admin (super-controlled operations)



---

2. Tech Stack (Strict)

Frontend:

Next.js (App Router)

TypeScript (mandatory)

Tailwind CSS

Axios (centralized API instance)


Backend:

Django

Django REST Framework

PostgreSQL

Celery + Redis (for background tasks, future-ready)


Storage:

Cloudinary (media uploads)


Payments:

Razorpay (webhook verification required)


Deployment:

Vercel (Frontend)

Render / VPS (Backend)


AI must NOT introduce other frameworks unless explicitly requested.


---

3. Backend Architecture Rules

3.1 App Structure

Each feature must be a separate Django app:

/apps users products orders custom_requests payments

Shared logic: /services /utils


---

3.2 Business Logic Rules

Business logic must NOT be inside views.

Use service layer for complex logic.

Use database transactions for payment-related operations.

Always validate data through serializers.



---

3.3 API Response Standard (MANDATORY)

Success Format:

{ "success": true, "data": {}, "message": "Action successful" }

Error Format:

{ "success": false, "error": "Error message" }

Never return raw Django responses without this structure.


---

3.4 Authentication Rules

Use JWT authentication.

Admin endpoints must require admin role.

Never expose sensitive fields in serializers.



---

4. Frontend Architecture Rules

4.1 Folder Structure

/app /components /services /hooks /types /lib


---

4.2 API Handling

Use centralized axios instance.

Do NOT call fetch directly in components.

Handle errors globally.

Use typed responses (TypeScript interfaces).



---

4.3 UI Rules

Follow VENOPAI_DESIGN_SYSTEM.md

Use reusable components.

Avoid inline styles.

Use Tailwind utility classes.



---

5. Naming Conventions

Backend:

snake_case for variables

PascalCase for classes

Verb-based function names (create_order, verify_payment)


Frontend:

PascalCase for components

camelCase for functions

useX format for hooks (useCart, useAuth)



---

6. Payment Rules

Always verify Razorpay webhook signature.

Never trust frontend payment confirmation.

Wrap order creation in atomic transaction.

Handle payment failure edge cases.



---

7. Database Rules

Follow VENOPAI_DATABASE_SCHEMA.md strictly.

Use foreign keys properly.

Add indexes on frequently queried fields.

Never create duplicate models.



---

8. Performance Rules

Use select_related / prefetch_related in Django.

Paginate large queries.

Avoid N+1 query problems.

Use caching for heavy read endpoints (future-ready).



---

9. Security Rules

Never hardcode secrets.

Always use environment variables.

Validate all user input.

Sanitize file uploads.



---

10. Code Quality Rules

Backend:

Use Black formatting

Follow PEP8

Keep functions small and modular


Frontend:

Strict TypeScript

ESLint clean

Reusable components only



---

11. What AI Must Avoid

Do not generate unnecessary complexity.

Do not introduce unused libraries.

Do not mix business logic into views.

Do not ignore defined API response structure.

Do not hardcode URLs.



---

12. AI Behavior Expectations

When generating code:

Follow existing architecture.

Reuse services layer if similar logic exists.

Maintain consistency across apps.

Optimize for scalability.

Write production-ready code only.


If uncertain:

Ask for clarification instead of guessing.



---

Conclusion

This document ensures AI behaves like a disciplined senior developer working on Venopai.

All generated code must align with:

PRD

TRD

Database Schema

Design System


Consistency > Speed.

End of Document.
