# API Contract (Current Backend Implementation)

This document describes the **current** API contract implemented in the Django backend under `/api/v1/` and `/admin/`.

- Base API prefix: `/api/v1/`
- Auth mechanism: JWT Bearer token (`Authorization: Bearer <access_token>`)
- Default API permission: `IsAuthenticated` unless a view overrides it
- Content type: `application/json` unless noted
- Trailing slashes are used on DRF router endpoints

---

## 1) Authentication Endpoints

### 1.1 Obtain JWT Token Pair
- **URL:** `/api/v1/auth/token/`
- **Method:** `POST`
- **Authentication required:** **No**

**Request body**
```json
{
  "email": "student@example.com",
  "password": "your-password"
}
```

**Success response structure (`200 OK`)**
```json
{
  "refresh": "<jwt-refresh-token>",
  "access": "<jwt-access-token>"
}
```

**Error response examples**
- `401 Unauthorized`
```json
{
  "detail": "No active account found with the given credentials"
}
```

**Validation rules**
- `email` and `password` must match an active user account.

**Status codes**
- `200 OK`
- `401 Unauthorized`

---

### 1.2 Refresh JWT Access Token
- **URL:** `/api/v1/auth/token/refresh/`
- **Method:** `POST`
- **Authentication required:** **No**

**Request body**
```json
{
  "refresh": "<jwt-refresh-token>"
}
```

**Success response structure (`200 OK`)**
```json
{
  "access": "<new-jwt-access-token>",
  "refresh": "<new-jwt-refresh-token>"
}
```
> Note: refresh rotation is enabled in settings, so a new refresh token may be returned.

**Error response examples**
- `401 Unauthorized`
```json
{
  "detail": "Token is invalid or expired",
  "code": "token_not_valid"
}
```

**Validation rules**
- `refresh` must be a valid, non-expired refresh token.

**Status codes**
- `200 OK`
- `401 Unauthorized`

---

## 2) Users Endpoints

- **URL prefix configured:** `/api/v1/users/`

### 2.1 Register User
- **URL:** `/api/v1/users/register/`
- **Method:** `POST`
- **Authentication required:** **No**

### 2.2 Referral Summary
- **URL:** `/api/v1/users/referral-summary/`
- **Method:** `GET`
- **Authentication required:** **Yes**

**Response structure (`200 OK`)**
```json
{
  "referral_code": "AB12CD34EF",
  "total_referrals": 5,
  "successful_referrals": 3,
  "pending_rewards": 2,
  "earned_rewards": "300.00",
  "referral_link": "http://localhost:3000/register/?ref=AB12CD34EF",
  "reward_coupon_codes": ["REF1234567890", "REFABCDEFGHIJ"]
}
```

---

## 3) Product Endpoints

Permission class: `IsAdminOrReadOnly`
- `GET/HEAD/OPTIONS`: public
- `POST/PUT/PATCH/DELETE`: staff user required (`request.user.is_staff == True`)

For product listing/retrieval, non-staff users only see products where `is_active=true`.

### 3.1 Products Collection
- **URL:** `/api/v1/products/`
- **Methods:** `GET`, `POST`

#### GET /api/v1/products/
- **Authentication required:** **No**

**Response structure (`200 OK`)**
```json
[
  {
    "id": 1,
    "category": 10,
    "category_name": "Laptops",
    "name": "Dell Inspiron 15",
    "slug": "dell-inspiron-15",
    "description": "Student laptop",
    "price": "50000.00",
    "sku": "DL-INSP-15",
    "stock_quantity": 10,
    "is_refurbished": false,
    "condition_grade": "A",
    "is_active": true,
    "created_at": "2026-03-02T00:00:00Z",
    "updated_at": "2026-03-02T00:00:00Z"
  }
]
```

**Error response examples**
- Usually none for normal list access

**Status codes**
- `200 OK`

#### POST /api/v1/products/
- **Authentication required:** **Yes (staff only)**

**Request body**
```json
{
  "category": 10,
  "name": "Dell Inspiron 15",
  "slug": "dell-inspiron-15",
  "description": "Student laptop",
  "price": "50000.00",
  "sku": "DL-INSP-15",
  "stock_quantity": 10,
  "is_refurbished": false,
  "condition_grade": "A",
  "is_active": true
}
```

**Success response structure (`201 Created`)**
- Same shape as product object above.

**Error response examples**
- `401 Unauthorized`
```json
{
  "detail": "Authentication credentials were not provided."
}
```
- `403 Forbidden`
```json
{
  "detail": "You do not have permission to perform this action."
}
```
- `400 Bad Request` (example)
```json
{
  "sku": ["product with this sku already exists."]
}
```

**Validation rules**
- `category` must reference an existing category.
- `name` max length 255.
- `slug` unique, max length 280 (auto-generated from name if omitted by model).
- `price` decimal (max_digits=12, decimal_places=2).
- `sku` unique, max length 64.
- `stock_quantity` non-negative integer.
- `condition_grade` max length 20.

**Status codes**
- `201 Created`
- `400 Bad Request`
- `401 Unauthorized`
- `403 Forbidden`

---

### 3.2 Product Detail
- **URL:** `/api/v1/products/{id}/`
- **Methods:** `GET`, `PUT`, `PATCH`, `DELETE`

**Authentication required**
- `GET`: No
- `PUT/PATCH/DELETE`: Yes (staff only)

**Request body (PUT/PATCH)**
- Same fields as product create.

**Success responses**
- `GET`/`PUT`/`PATCH`: product object (`200 OK`)
- `DELETE`: empty body (`204 No Content`)

**Error response examples**
- `404 Not Found`
```json
{
  "detail": "No Product matches the given query."
}
```
- `403 Forbidden` / `401 Unauthorized` for non-staff writes

**Status codes**
- `200 OK`
- `204 No Content`
- `400 Bad Request`
- `401 Unauthorized`
- `403 Forbidden`
- `404 Not Found`

---

### 3.3 Categories
- **Collection URL:** `/api/v1/products/categories/` (`GET`, `POST`)
- **Detail URL:** `/api/v1/products/categories/{id}/` (`GET`, `PUT`, `PATCH`, `DELETE`)
- **Authentication required:** read public; writes staff only

**Category object**
```json
{
  "id": 1,
  "name": "Laptops",
  "slug": "laptops",
  "description": "",
  "is_active": true,
  "created_at": "2026-03-02T00:00:00Z",
  "updated_at": "2026-03-02T00:00:00Z"
}
```

**Validation rules**
- `name` unique, max length 120
- `slug` unique, max length 140 (auto-generated from name if omitted)

**Status codes**
- `200 OK`, `201 Created`, `204 No Content`, `400`, `401`, `403`, `404`

---

### 3.4 Product Images
- **Collection URL:** `/api/v1/products/images/` (`GET`, `POST`)
- **Detail URL:** `/api/v1/products/images/{id}/` (`GET`, `PUT`, `PATCH`, `DELETE`)
- **Authentication required:** read public; writes staff only

**Product image object**
```json
{
  "id": 1,
  "product": 1,
  "image_url": "https://example.com/image.jpg",
  "alt_text": "Front view",
  "is_primary": true,
  "sort_order": 0,
  "created_at": "2026-03-02T00:00:00Z",
  "updated_at": "2026-03-02T00:00:00Z"
}
```

**Validation rules**
- `product` must exist
- `image_url` must be valid URL
- `alt_text` max length 255
- `sort_order` non-negative small integer

**Status codes**
- `200 OK`, `201 Created`, `204 No Content`, `400`, `401`, `403`, `404`

---

### 3.5 Inventory
- **Collection URL:** `/api/v1/products/inventory/` (`GET`, `POST`)
- **Detail URL:** `/api/v1/products/inventory/{id}/` (`GET`, `PUT`, `PATCH`, `DELETE`)
- **Authentication required:** read public; writes staff only

**Inventory object**
```json
{
  "id": 1,
  "product": 1,
  "quantity": 50,
  "reserved_quantity": 10,
  "reorder_level": 5,
  "created_at": "2026-03-02T00:00:00Z",
  "updated_at": "2026-03-02T00:00:00Z"
}
```

**Validation rules**
- `product` must exist and can only have one inventory row (OneToOne)
- `quantity`, `reserved_quantity`, `reorder_level` are non-negative integers

**Status codes**
- `200 OK`, `201 Created`, `204 No Content`, `400`, `401`, `403`, `404`

---

## 4) Cart Endpoints

All cart endpoints require JWT auth.

### 4.1 Carts
- **Collection URL:** `/api/v1/orders/carts/` (`GET`, `POST`)
- **Detail URL:** `/api/v1/orders/carts/{id}/` (`GET`, `PUT`, `PATCH`, `DELETE`)
- **Authentication required:** **Yes**

**Behavior**
- Queryset is user-scoped (`Cart.objects.filter(user=request.user)`).
- On create, `user` is forced to authenticated user.

**Request body (POST/PUT/PATCH)**
```json
{
  "is_active": true
}
```
(`user`, `id`, `created_at`, `updated_at` are read-only)

**Cart response object**
```json
{
  "id": 1,
  "user": "<uuid>",
  "is_active": true,
  "created_at": "2026-03-02T00:00:00Z",
  "updated_at": "2026-03-02T00:00:00Z"
}
```

**Error response examples**
- `401 Unauthorized`
- `400 Bad Request` (e.g. unique active cart constraint)
```json
{
  "non_field_errors": ["The fields user must make a unique set."]
}
```

**Validation rules**
- One active cart per user (DB constraint `unique_active_cart_per_user`).

**Status codes**
- `200 OK`, `201 Created`, `204 No Content`, `400`, `401`, `404`

---

### 4.2 Cart Items
- **Collection URL:** `/api/v1/orders/cart-items/` (`GET`, `POST`)
- **Detail URL:** `/api/v1/orders/cart-items/{id}/` (`GET`, `PUT`, `PATCH`, `DELETE`)
- **Authentication required:** **Yes**

**Behavior**
- Queryset scoped to current user cart items.
- Serializer enforces cart ownership.

**Request body (POST/PUT/PATCH)**
```json
{
  "cart": 1,
  "product": 12,
  "quantity": 2
}
```

**Response object**
```json
{
  "id": 5,
  "cart": 1,
  "product": 12,
  "quantity": 2,
  "created_at": "2026-03-02T00:00:00Z",
  "updated_at": "2026-03-02T00:00:00Z"
}
```

**Error response examples**
- `400 Bad Request` ownership validation
```json
{
  "cart": ["You can only add items to your own cart."]
}
```
- `400 Bad Request` duplicate product in same cart
```json
{
  "non_field_errors": ["The fields cart, product must make a unique set."]
}
```
- `401 Unauthorized`

**Validation rules**
- `cart` must exist and belong to requesting user.
- `product` must exist.
- `quantity` is positive integer with minimum 1.
- Unique `(cart, product)`.

**Status codes**
- `200 OK`, `201 Created`, `204 No Content`, `400`, `401`, `404`

---

## 5) Order Endpoints

All order endpoints require JWT auth.

### 5.1 Orders
- **Collection URL:** `/api/v1/orders/` (`GET`, `POST`)
- **Detail URL:** `/api/v1/orders/{id}/` (`GET`, `PUT`, `PATCH`, `DELETE`)
- **Authentication required:** **Yes**

**Behavior**
- Queryset scoped to current user orders.
- On create, `user` is forced to current user.

**Request body (POST/PUT/PATCH)**
```json
{
  "total_amount": "999.00",
  "status": "pending",
  "payment_status": "pending",
  "tracking_id": "TRACK-001"
}
```

**Order response object**
```json
{
  "id": 1,
  "user": "<uuid>",
  "total_amount": "999.00",
  "status": "pending",
  "payment_status": "pending",
  "tracking_id": "TRACK-001",
  "created_at": "2026-03-02T00:00:00Z",
  "updated_at": "2026-03-02T00:00:00Z"
}
```

**Error response examples**
- `401 Unauthorized`
- `400 Bad Request`
```json
{
  "total_amount": ["Ensure this value is greater than or equal to 0.01."]
}
```

**Validation rules**
- `total_amount` decimal >= `0.01`.
- `status` one of: `pending|confirmed|shipped|delivered|cancelled`.
- `payment_status` one of: `pending|paid|failed|refunded`.
- `tracking_id` unique if provided.

**Status codes**
- `200 OK`, `201 Created`, `204 No Content`, `400`, `401`, `404`

---

### 5.2 Order Items
- **Collection URL:** `/api/v1/orders/items/` (`GET`, `POST`)
- **Detail URL:** `/api/v1/orders/items/{id}/` (`GET`, `PUT`, `PATCH`, `DELETE`)
- **Authentication required:** **Yes**

**Behavior**
- Queryset scoped to items where `order.user == request.user`.
- Serializer enforces order ownership.

**Request body**
```json
{
  "order": 1,
  "product": 12,
  "quantity": 1,
  "price": "999.00"
}
```

**Response object**
```json
{
  "id": 10,
  "order": 1,
  "product": 12,
  "quantity": 1,
  "price": "999.00",
  "created_at": "2026-03-02T00:00:00Z",
  "updated_at": "2026-03-02T00:00:00Z"
}
```

**Error response examples**
- `400 Bad Request` ownership validation
```json
{
  "order": ["You can only add items to your own order."]
}
```
- `400 Bad Request` quantity/price validation

**Validation rules**
- `order` must belong to authenticated user.
- `product` must exist.
- `quantity` >= 1.
- `price` >= 0.01.

**Status codes**
- `200 OK`, `201 Created`, `204 No Content`, `400`, `401`, `404`

---

### 5.3 Shipping Addresses
- **Collection URL:** `/api/v1/orders/shipping-addresses/` (`GET`, `POST`)
- **Detail URL:** `/api/v1/orders/shipping-addresses/{id}/` (`GET`, `PUT`, `PATCH`, `DELETE`)
- **Authentication required:** **Yes**

**Behavior**
- Queryset scoped to addresses where `order.user == request.user`.
- Serializer enforces order ownership.

**Request body**
```json
{
  "order": 1,
  "full_name": "John Doe",
  "phone_number": "9999999999",
  "address_line_1": "123 Main St",
  "address_line_2": "Apartment 4B",
  "city": "Delhi",
  "state": "Delhi",
  "postal_code": "110001",
  "country": "India"
}
```

**Response object**
```json
{
  "id": 2,
  "order": 1,
  "full_name": "John Doe",
  "phone_number": "9999999999",
  "address_line_1": "123 Main St",
  "address_line_2": "Apartment 4B",
  "city": "Delhi",
  "state": "Delhi",
  "postal_code": "110001",
  "country": "India",
  "created_at": "2026-03-02T00:00:00Z",
  "updated_at": "2026-03-02T00:00:00Z"
}
```

**Error response examples**
- `400 Bad Request` ownership validation
```json
{
  "order": ["You can only add a shipping address to your own order."]
}
```
- `400 Bad Request` one-to-one violation
```json
{
  "order": ["shipping address with this order already exists."]
}
```

**Validation rules**
- `order` must belong to authenticated user.
- One shipping address per order (`OneToOneField`).
- Field max lengths:
  - `full_name` 255
  - `phone_number` 20
  - `address_line_1` 255
  - `address_line_2` 255 (optional)
  - `city` 100
  - `state` 100
  - `postal_code` 20
  - `country` 100 (default `India`)

**Status codes**
- `200 OK`, `201 Created`, `204 No Content`, `400`, `401`, `404`

---

## 6) Payment Endpoints

### 6.1 Create Razorpay Order
- **URL:** `/api/v1/payments/create-order/`
- **Method:** `POST`
- **Authentication required:** **Yes**

**Headers**
- Optional: `Idempotency-Key` header (`HTTP_IDEMPOTENCY_KEY`)

**Request body**
```json
{
  "order_id": 1,
  "idempotency_key": "idem-123"
}
```
> `idempotency_key` can be sent in body or `Idempotency-Key` header.

**Success responses**
- `201 Created` (new payment intent)
```json
{
  "payment_id": 1,
  "razorpay_order_id": "order_ABC123",
  "amount": 99900,
  "currency": "INR",
  "key_id": "rzp_test_key"
}
```
- `200 OK` (same idempotency key reused for same order)

**Error response examples**
- `400 Bad Request`
```json
{
  "detail": "order_id and idempotency_key are required."
}
```
- `404 Not Found`
```json
{
  "detail": "Order not found."
}
```
- `409 Conflict`
```json
{
  "detail": "Order already paid."
}
```
```json
{
  "detail": "Idempotency key is already used."
}
```
```json
{
  "detail": "Duplicate payment attempt detected."
}
```
- `500 Internal Server Error`
```json
{
  "detail": "Payment gateway configuration error."
}
```
- `502 Bad Gateway`
```json
{
  "detail": "Unable to create payment order."
}
```

**Validation rules**
- `order_id` must exist and belong to authenticated user.
- order must not already be paid.
- `idempotency_key` required and globally unique per payment intent.

**Status codes**
- `200 OK`
- `201 Created`
- `400 Bad Request`
- `401 Unauthorized`
- `404 Not Found`
- `409 Conflict`
- `500 Internal Server Error`
- `502 Bad Gateway`

---

### 6.2 Verify Razorpay Payment
- **URL:** `/api/v1/payments/verify/`
- **Method:** `POST`
- **Authentication required:** **Yes**

**Request body**
```json
{
  "razorpay_order_id": "order_ABC123",
  "razorpay_payment_id": "pay_ABC123",
  "razorpay_signature": "<signature>"
}
```

**Success response (`200 OK`)**
```json
{
  "detail": "Payment verified successfully."
}
```

**Error response examples**
- `400 Bad Request`
```json
{
  "detail": "Missing payment verification fields."
}
```
```json
{
  "detail": "Invalid payment signature."
}
```
- `404 Not Found`
```json
{
  "detail": "Payment not found."
}
```
- `409 Conflict`
```json
{
  "detail": "Order already paid."
}
```
```json
{
  "detail": "Duplicate payment id."
}
```

**Validation rules**
- All three fields required.
- `razorpay_order_id` payment must belong to requesting user.
- Signature must match server-computed HMAC.
- `razorpay_payment_id` must not already be used by another payment.

**Status codes**
- `200 OK`
- `400 Bad Request`
- `401 Unauthorized`
- `404 Not Found`
- `409 Conflict`

---

### 6.3 Razorpay Webhook
- **URL:** `/api/v1/payments/webhook/`
- **Method:** `POST`
- **Authentication required:** **No (signature-based)**

**Headers**
- Required: `X-Razorpay-Signature`
- Optional (idempotency): `X-Razorpay-Event-Id`

**Request body**
- Raw Razorpay webhook JSON payload.

**Success responses**
- `200 OK`
```json
{
  "detail": "Webhook processed."
}
```
or
```json
{
  "detail": "Webhook already processed."
}
```
or
```json
{
  "detail": "Webhook accepted."
}
```

**Error response examples**
- `400 Bad Request`
```json
{
  "detail": "Invalid webhook signature."
}
```
- `500 Internal Server Error`
```json
{
  "detail": "Webhook configuration error."
}
```

**Validation rules**
- Webhook secret must be configured.
- HMAC signature must match raw request body.
- Duplicate events are deduplicated by event id.

**Status codes**
- `200 OK`
- `400 Bad Request`
- `500 Internal Server Error`

---

## 7) Admin Endpoints

### 7.1 Django Admin Site
- **URL:** `/admin/`
- **Methods:** browser-driven admin routes (primarily `GET` + form `POST`)
- **Authentication required:** **Yes** (Django admin session auth; staff/superuser)
- **Response type:** HTML (not JSON)

**Current behavior**
- Custom dashboard context added to admin index page.
- Optional query params on admin index:
  - `start_date=YYYY-MM-DD`
  - `end_date=YYYY-MM-DD`

**Validation behavior**
- Invalid dates are handled by fallback logic and warning messages.

**Status codes (typical)**
- `200 OK` for authenticated admin users
- `302 Redirect` to login if not authenticated

---

### 7.2 Admin Panel API Prefix
- **URL prefix configured:** `/api/v1/adminpanel/`
- **Current implementation:** `adminpanel/urls.py` is empty.

There are currently **no API endpoints** under this prefix.

---

## 8) Common Error Shapes (DRF)

Common DRF error payload patterns used across endpoints:

- Permission/authentication error
```json
{
  "detail": "Authentication credentials were not provided."
}
```

- Field validation error
```json
{
  "field_name": ["Error message"]
}
```

- Not found error
```json
{
  "detail": "Not found."
}
```

---

## 9) Notes on Accuracy

This contract is based on the current source implementation in:
- `Backend/core/urls.py`, `Backend/core/api_urls.py`
- `Backend/products/*`
- `Backend/orders/*`
- `Backend/payments/*`
- `Backend/adminpanel/*`
- `Backend/core/settings/base.py`

If serializers/views/models or router registration change, this contract should be updated accordingly.
