# VENOPAI

# Technical Requirements Document (TRD)

---

# 1. System Overview

Venopai is a scalable, vertically integrated engineering commerce and custom manufacturing platform.

Architecture Style:

* Decoupled frontend and backend
* REST-based API communication
* Cloud-native deployment
* Modular, scalable services

Core Stack:

* Frontend: Next.js (App Router)
* Backend: Django + Django REST Framework
* Database: PostgreSQL
* Cache & Queue: Redis
* Background Jobs: Celery
* Storage: Cloudinary
* Payments: Razorpay
* Hosting: Vercel (Frontend), Render/Railway (Backend)

---

# 2. High-Level Architecture

Client (Browser / Mobile)
↓
Next.js Frontend (Vercel)
↓ REST API (HTTPS)
Django Backend (Render/Railway)
↓
PostgreSQL Database
↓
Redis (Caching + Celery Broker)
↓
Cloudinary (File Storage)

---

# 3. Frontend Technical Requirements

## 3.1 Framework

* Next.js (App Router)
* TypeScript (strict mode)
* Server Components where applicable
* Client Components for interactive modules

## 3.2 UI Stack

* TailwindCSS
* Shadcn UI
* Framer Motion (animations)
* Responsive design (mobile-first)

## 3.3 State Management

* React Query (server state)
* Zustand (client state)

## 3.4 Performance Requirements

* Page load under 2 seconds (target)
* Image optimization enabled
* Lazy loading for heavy components
* Code splitting per route

## 3.5 Security Requirements

* JWT stored securely (httpOnly cookies preferred)
* CSRF protection
* Input validation before API calls

---

# 4. Backend Technical Requirements

## 4.1 Framework

* Django
* Django REST Framework
* JWT Authentication

## 4.2 API Standards

* RESTful structure
* JSON responses only
* Versioned APIs (/api/v1/)
* Proper HTTP status codes

## 4.3 Core Apps Structure

* users
* products
* inventory
* orders
* manufacturing
* payments
* admin_control
* ai_engine

---

# 5. Database Design (Core Entities)

## 5.1 User Table

* id
* name
* email
* password_hash
* role (admin/student)
* created_at

## 5.2 Product Table

* id
* name
* description
* category
* price
* sku
* stock_quantity
* is_refurbished
* condition_grade
* created_at

## 5.3 Order Table

* id
* user_id
* total_amount
* status
* payment_status
* tracking_id
* created_at

## 5.4 Order Items

* id
* order_id
* product_id
* quantity
* price

## 5.5 Manufacturing Request

* id
* user_id
* description
* file_url
* quoted_price
* status
* assigned_admin
* created_at

## 5.6 Payment Table

* id
* order_id
* razorpay_order_id
* payment_status
* amount

Indexes must be added on:

* user_id
* product_id
* order_id
* status fields

---

# 6. Manufacturing Pipeline Logic

State Machine:

* REQUEST_RECEIVED
* UNDER_REVIEW
* QUOTED
* PAID
* IN_PRODUCTION
* TESTING
* PACKED
* DISPATCHED

Transitions must be validated.
No skipping states without admin override.

---

# 7. AI Engine Architecture

## 7.1 Phase 1 Scope

* Product recommendations
* Bundle suggestions
* Branch-based suggestions

## 7.2 Technical Implementation

* Product embeddings stored in PostgreSQL (pgvector)
* Semantic search API endpoint
* Redis caching for frequent queries
* OpenRouter small model for limited assistant responses

Cost control:

* Rate limiting per user
* Token usage logging

---

# 8. Payment Integration

## Razorpay Flow

1. Backend creates Razorpay order
2. Frontend opens Razorpay checkout
3. Payment success callback
4. Backend verifies signature
5. Order status updated to PAID

Security:

* Signature verification mandatory
* Payment status double-checked

---

# 9. File Upload System

* Direct upload from frontend to Cloudinary
* Backend stores secure file URL
* File size limit enforcement
* File type validation

---

# 10. Admin Panel System

## Features

* Role-based access control
* Protected routes
* Dashboard analytics queries optimized
* Kanban board (manufacturing pipeline)

Admin authentication must require elevated role check.

---

# 11. Caching Strategy

Redis usage:

* Product listing cache
* Recommendation cache
* Session cache
* Rate limiting

Cache invalidation on:

* Product update
* Stock update

---

# 12. Background Jobs (Celery)

Tasks:

* Invoice generation
* Email notifications
* Manufacturing stage alerts
* AI embedding updates

Celery broker: Redis

---

# 13. Security Requirements

* HTTPS mandatory
* JWT expiration
* Rate limiting
* SQL injection protection (ORM)
* XSS protection
* Input sanitization
* Admin route protection
* Logging of critical actions

---

# 14. Scalability Considerations

* Stateless backend
* Horizontal scaling ready
* Database indexing
* Separate read replicas (future)
* CDN for static assets

---

# 15. Monitoring & Logging

* Error logging (Sentry recommended)
* Server monitoring
* Payment failure alerts
* Manufacturing delay alerts

---

# 16. Deployment Pipeline

* GitHub repository
* CI/CD pipeline
* Automatic deployment on push
* Environment variable separation (dev/staging/prod)

---

# 17. Future Enhancements (Technical)

* Microservices split if scale increases
* Dedicated AI service
* Vendor panel module
* Warehouse management system

---

# 18. Non-Functional Requirements

* High availability
* Data consistency
* Clean code architecture
* Maintainable modular structure
* Scalable infrastructure

---

# 19. Detailed Database Schema Design

This section defines production-level relational schema structure with relationships, constraints, and normalization considerations.

---

## 19.1 Users Table

Table: users

* id (UUID, PK)
* full_name (varchar 150)
* email (varchar 255, unique, indexed)
* password_hash (text)
* role (enum: ADMIN, STUDENT)
* phone_number (varchar 15, nullable)
* is_active (boolean, default true)
* created_at (timestamp)
* updated_at (timestamp)

Relationship:

* One-to-Many with orders
* One-to-Many with manufacturing_requests

---

## 19.2 Categories Table

Table: categories

* id (UUID, PK)
* name (varchar 120)
* slug (varchar 150, unique)
* parent_id (FK → categories.id, nullable)
* created_at (timestamp)

Relationship:

* One-to-Many with products
* Self-referencing (hierarchical categories)

---

## 19.3 Products Table

Table: products

* id (UUID, PK)
* name (varchar 255)
* description (text)
* category_id (FK → categories.id)
* price (decimal 10,2)
* sku (varchar 100, unique, indexed)
* stock_quantity (integer)
* is_refurbished (boolean)
* condition_grade (enum: A, B, C, nullable)
* battery_health_percent (integer, nullable)
* is_active (boolean, default true)
* created_at (timestamp)
* updated_at (timestamp)

Relationship:

* Many-to-One with categories
* One-to-Many with order_items

Indexes:

* sku
* category_id
* is_active

---

## 19.4 Product Images Table

Table: product_images

* id (UUID, PK)
* product_id (FK → products.id, indexed)
* image_url (text)
* is_primary (boolean)

Relationship:

* Many-to-One with products

---

## 19.5 Bundles Table

Table: bundles

* id (UUID, PK)
* name (varchar 255)
* description (text)
* discount_percent (decimal 5,2)
* created_at (timestamp)

Table: bundle_items

* id (UUID, PK)
* bundle_id (FK → bundles.id)
* product_id (FK → products.id)
* quantity (integer)

Relationship:

* Many-to-Many between products and bundles via bundle_items

---

## 19.6 Orders Table

Table: orders

* id (UUID, PK)
* user_id (FK → users.id, indexed)
* total_amount (decimal 10,2)
* order_status (enum: PENDING, PAID, SHIPPED, DELIVERED, CANCELLED)
* payment_status (enum: INITIATED, SUCCESS, FAILED, REFUNDED)
* tracking_id (varchar 255, nullable)
* created_at (timestamp)
* updated_at (timestamp)

Relationship:

* Many-to-One with users
* One-to-Many with order_items
* One-to-One with payments

---

## 19.7 Order Items Table

Table: order_items

* id (UUID, PK)
* order_id (FK → orders.id, indexed)
* product_id (FK → products.id)
* quantity (integer)
* unit_price (decimal 10,2)

Relationship:

* Many-to-One with orders
* Many-to-One with products

---

## 19.8 Payments Table

Table: payments

* id (UUID, PK)
* order_id (FK → orders.id, unique)
* razorpay_order_id (varchar 255, indexed)
* razorpay_payment_id (varchar 255, nullable)
* amount (decimal 10,2)
* payment_status (enum: INITIATED, SUCCESS, FAILED, REFUNDED)
* created_at (timestamp)

Relationship:

* One-to-One with orders

---

## 19.9 Manufacturing Requests Table

Table: manufacturing_requests

* id (UUID, PK)
* user_id (FK → users.id)
* title (varchar 255)
* description (text)
* file_url (text)
* quoted_price (decimal 10,2, nullable)
* status (enum: REQUEST_RECEIVED, UNDER_REVIEW, QUOTED, PAID, IN_PRODUCTION, TESTING, PACKED, DISPATCHED)
* assigned_admin_id (FK → users.id, nullable)
* tracking_id (varchar 255, nullable)
* created_at (timestamp)
* updated_at (timestamp)

Relationship:

* Many-to-One with users (student)
* Many-to-One with users (admin via assigned_admin_id)

---

## 19.10 Manufacturing Logs Table

Table: manufacturing_logs

* id (UUID, PK)
* manufacturing_request_id (FK → manufacturing_requests.id)
* status (same enum as above)
* updated_by (FK → users.id)
* timestamp (timestamp)

Purpose:

* Track full status transition history

---

## 19.11 AI Embeddings Table

Table: product_embeddings

* id (UUID, PK)
* product_id (FK → products.id)
* embedding_vector (vector type via pgvector)
* created_at (timestamp)

Purpose:

* Store semantic embeddings for recommendation engine

---

## 19.12 Discount & Coupon Table

Table: coupons

* id (UUID, PK)
* code (varchar 50, unique)
* discount_type (enum: PERCENTAGE, FIXED)
* discount_value (decimal 10,2)
* valid_from (timestamp)
* valid_to (timestamp)
* usage_limit (integer)
* is_active (boolean)

Table: coupon_usage

* id (UUID, PK)
* coupon_id (FK → coupons.id)
* user_id (FK → users.id)
* order_id (FK → orders.id)

---

## 19.13 Inventory Transactions Table

Table: inventory_transactions

* id (UUID, PK)
* product_id (FK → products.id)
* change_type (enum: PURCHASE, RESTOCK, MANUAL_ADJUSTMENT)
* quantity_changed (integer)
* reference_id (UUID, nullable)
* created_at (timestamp)

Purpose:

* Maintain inventory audit trail

---

# 20. Relationship Summary

* One User → Many Orders
* One User → Many Manufacturing Requests
* One Category → Many Products
* One Product → Many Order Items
* One Order → One Payment
* One Manufacturing Request → Many Logs
* Many Products ↔ Many Bundles

All foreign keys must enforce referential integrity.
Cascading delete should be carefully controlled (soft delete preferred for orders and payments).

---

END OF TRD

