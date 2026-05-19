# Venopai — Visual Development Map

**Generated:** May 16, 2026  
**Companion doc:** `PROJECT_RECOVERY_REPORT.md`

This document maps **what exists**, **how parts connect**, and **what is planned but missing**—using Mermaid diagrams for navigation and planning.

---

## Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | Implemented & wired |
| ⚠️ | Partial / split implementation |
| ❌ | Planned in docs, not in code |
| 🔗 | Integration gap |

---

# 1. Feature Dependency Graph

Features build on lower layers. Arrows mean **“depends on”** or **“requires working”**.

```mermaid
flowchart TB
    subgraph foundation [Foundation Layer]
        AUTH[JWT Auth + Users]
        DB[(PostgreSQL / SQLite)]
        REDIS[(Redis Cache + Channels)]
    end

    subgraph catalog [Catalog Layer]
        PROD[Products + Categories]
        INV[Inventory + Stock]
        IMG[Product Images URL]
        SEARCH[Product Search API]
        FLASH[Flash Sales API]
        REV[Reviews]
    end

    subgraph commerce [Commerce Layer]
        CART_S[Server Cart API]
        CART_C[Client Cart Context]
        ORDER[Orders + OrderItems]
        COUPON[Coupons]
        SHIP[Shipping Address + Events]
    end

    subgraph payments [Payments Layer]
        RZP[Razorpay Create/Verify]
        WH[Payment Webhook]
        RETRY[Payment Retry]
        REFUND[Refund API]
    end

    subgraph growth [Growth Layer]
        REF[Referral Program]
        WISH[Wishlist]
        PW[Price Watch]
        REC[Recommendations Service]
        BOT[Chatbot OpenAI]
    end

    subgraph ops [Operations Layer]
        EMAIL[Order Emails]
        ABANDON[Abandoned Cart CMD]
        ADMIN_API[Admin Order APIs]
        ANALYTICS[Admin Analytics]
        WS[Order WebSocket]
    end

    subgraph marketplace [Marketplace Layer]
        VENDOR[Vendor Profile + Dashboard APIs]
        VORD[VendorOrder Split]
    end

  AUTH --> PROD
  DB --> PROD
  PROD --> INV
  PROD --> IMG
  PROD --> SEARCH
  PROD --> FLASH
  PROD --> REV

  AUTH --> CART_S
  PROD --> CART_S
  CART_S --> ORDER
  CART_C -.->|🔗 not synced| ORDER
  PROD --> ORDER
  INV --> ORDER
  COUPON --> ORDER
  ORDER --> SHIP

  ORDER --> RZP
  RZP --> WH
  ORDER --> RETRY
  ORDER --> REFUND
  RZP --> INV

  AUTH --> REF
  ORDER --> REF
  AUTH --> WISH
  PROD --> WISH
  PROD --> PW
  ORDER --> REC
  REC --> BOT
  AUTH --> BOT

  ORDER --> EMAIL
  CART_S --> ABANDON
  ORDER --> ADMIN_API
  ORDER --> ANALYTICS
  ORDER --> WS
  REDIS --> WS
  REDIS --> ANALYTICS

  ORDER --> VORD
  VENDOR --> VORD
  PROD --> VENDOR

  subgraph missing [❌ Planned Not Built]
    MFG[Manufacturing Pipeline]
    CLOUD[Cloudinary Upload]
    STUDENT[Student Verification]
  end

  PROD -.-> MFG
  IMG -.-> CLOUD
  AUTH -.-> STUDENT
```

### Feature dependency table (quick reference)

| Feature | Depends on | Blocks |
|---------|------------|--------|
| Checkout / Pay | Auth, Products, Orders, Razorpay | Fulfillment, Referral reward |
| Referral rewards | Paid order + Coupon system | — |
| Reviews | Auth, Paid order (verified) | — |
| Admin ship/deliver | Orders, Shipping events | Customer tracking UI |
| Vendor earnings | Paid order, VendorProduct | Vendor frontend ❌ |
| Chatbot order status | Auth, Orders | — |
| Abandoned cart email | Server cart, SMTP | Celery beat ⚠️ |

---

# 2. Frontend ↔ Backend Relationship Map

```mermaid
flowchart LR
    subgraph browser [Browser - Next.js 14]
        subgraph pages [App Router Pages]
            HOME["/ home"]
            PRODS["/products"]
            PDET["/products/slug"]
            CARTP["/cart"]
            CHK["/checkout"]
            WISH_P["/wishlist"]
            REF_P["/referral"]
            ORD["/account/orders"]
            LOGIN["/login"]
            REG["/register disabled"]
            ADM["/admin/*"]
            DASH["/dashboard"]
        end

        subgraph state [Client State]
            ZUST[Zustand auth-store]
            RQ[React Query]
            CTX[CartContext local]
            AX[axios apiClient]
        end

        MW[middleware.ts cookie gate]
    end

    subgraph api [Django REST /api/v1]
        AUTH_API[auth/token]
        USER_API[users/*]
        PROD_API[products/*]
        ORD_API[orders/*]
        PAY_API[payments/*]
        WL_API[wishlist/*]
        ADM_API[admin/*]
        CHAT_API[chatbot/*]
        PW_API[price-watch/*]
        VEN_API[vendors/*]
    end

    subgraph no_fe [Backend Only - No UI]
        FLASH_API[flash-sales/*]
        CHAT_ONLY[chatbot]
        PW_ONLY[price-watch]
        VEN_ONLY[vendors/*]
        SEARCH_API[search/*]
    end

    HOME --> CTX
    HOME -.->|mock data| PROD_API
    PRODS --> RQ --> PROD_API
    PDET --> RQ --> PROD_API
    PDET --> RQ --> REV_API[reviews/*]
    PDET --> WL_API
    CARTP --> RQ --> ORD_API
    CHK --> CTX
    CHK --> ORD_API
    CHK --> PAY_API
    WISH_P --> RQ --> WL_API
    WISH_P --> CTX
    REF_P --> RQ --> USER_API
    ORD --> RQ --> ORD_API
    ORD --> PAY_API
    LOGIN --> ZUST --> AUTH_API
    REG -.->|disabled| USER_API
    ADM --> RQ --> ADM_API
    DASH --> RQ --> ADM_API

    AX --> AUTH_API
    AX --> USER_API
    AX --> PROD_API
    AX --> ORD_API
    AX --> PAY_API

    MW --> USER_API

    style CTX fill:#fef3c7,stroke:#d97706
    style REG fill:#fee2e2,stroke:#dc2626
    style no_fe fill:#f3f4f6,stroke:#9ca3af
```

### Integration status matrix

| Frontend surface | Backend API | Sync quality |
|------------------|-------------|--------------|
| `/products`, `/products/[slug]` | `products/`, `reviews/` | ✅ Good |
| `/cart` | `orders/carts/`, `cart-items/` | ✅ Good |
| `/checkout` | `orders/create/`, `payments/*` | ⚠️ Uses **local** cart, not server |
| `/` home | — | ❌ Hardcoded products |
| `/wishlist` | `wishlist/` | ⚠️ Add-to-cart → local context |
| `/referral` | `users/referral-summary/` | ✅ Good |
| `/account/orders` | `orders/my-orders/` | ✅ Good |
| `/login` | `auth/token/` | ⚠️ No refresh interceptor |
| Chatbot, Price watch, Vendors, Flash sales | APIs exist | ❌ No pages |

---

# 3. API Flow Map

## 3.1 Global API topology

```mermaid
flowchart TB
    CLIENT[Next.js Client / Razorpay JS / Webhook]

    CLIENT -->|HTTPS JSON| GW["/api/v1/"]

    GW --> HEALTH[health/]
    GW --> AUTH[auth/token refresh]
    GW --> USERS[users/]
    GW --> PRODUCTS[products/ categories images inventory]
    GW --> FLASH[flash-sales/]
    GW --> REVIEWS[reviews/]
    GW --> SEARCH[search/ suggestions]
    GW --> ORDERS[orders/ carts cart-items coupons shipping]
    GW --> PAYMENTS[payments/]
    GW --> WISHLIST[wishlist/]
    GW --> CHATBOT[chatbot/message/]
    GW --> PRICEW[price-watch/]
    GW --> VENDORS[vendors/]
    GW --> ADMIN[admin/]

    ORDERS --> DB[(Database)]
    PRODUCTS --> DB
    PAYMENTS --> DB
    PAYMENTS --> RZP_EXT[Razorpay API]
    CHATBOT --> OAI[OpenAI API]

    PAYMENTS --> WH_IN[payments/webhook/]
    RZP_EXT --> WH_IN

    ORDERS --> REDIS[(Redis)]
    ADMIN --> REDIS
    PRODUCTS --> REDIS

    ORDERS --> WS_OUT[ws/orders/id/]
    WS_OUT --> REDIS
```

## 3.2 Checkout & payment sequence

```mermaid
sequenceDiagram
    autonumber
    participant U as User Browser
    participant FE as Checkout Page
    participant API as Django API
    participant DB as PostgreSQL
    participant RZP as Razorpay

    U->>FE: Pay with Razorpay
    FE->>API: POST /orders/create/ {items}
    API->>DB: Order + OrderItems pending
    API-->>FE: order id amount

    FE->>API: POST /payments/create-order/
    API->>RZP: Create order
    RZP-->>API: razorpay_order_id
    API-->>FE: key_id order_id amount

    FE->>RZP: Checkout.js modal
    RZP-->>FE: payment success payload

    FE->>API: POST /payments/verify/
    API->>API: HMAC verify signature
    API->>DB: Payment captured stock deduct
    API->>DB: OrderEvent EmailEvent
    API-->>FE: success

    FE->>U: redirect /order-success

    Note over FE,DB: Shipping address NOT sent from checkout UI
    Note over API: Email sent synchronously in request
```

## 3.3 Admin order fulfillment sequence

```mermaid
sequenceDiagram
    participant A as Admin Browser
    participant FE as /admin/orders/id
    participant API as /api/v1/admin/
    participant DB as Database
    participant WS as WebSocket Channel

    A->>FE: Update status / Ship / Deliver
    FE->>API: POST admin/orders/id/status/
    API->>DB: Order + OrderEvent
    API->>DB: ShippingEvent optional
    API->>API: send_order_email sync
    API->>WS: broadcast order.update
    API-->>FE: AdminOrderDetail JSON
```

---

# 4. User Flow (Customer / Student)

```mermaid
flowchart TD
    START([Landing /]) --> CHOICE{Authenticated?}

    CHOICE -->|No| BROWSE_G[Browse mock products on /]
    BROWSE_G --> LOGIN_G[/login]
    LOGIN_G -->|JWT| AUTH_OK[Auth OK]

    CHOICE -->|Yes| AUTH_OK
    BROWSE_G --> PROD_LIST[/products API listing]
    LOGIN_G --> PROD_LIST

    PROD_LIST --> PDETAIL[Product detail + reviews + wishlist]
    PDETAIL --> ADD_LOCAL[Add to cart - local context]
    PDETAIL --> ADD_WISH[Add to wishlist API]

    ADD_LOCAL --> HOME_CART[Cart drawer on home]
    ADD_WISH --> WISH_PAGE[/wishlist]
    WISH_PAGE --> MOVE_CART[Move to cart - local]

    AUTH_OK --> CART_SERVER[/cart - server API]
    ADD_LOCAL --> CHK[/checkout - local cart]
    MOVE_CART --> CHK
    CART_SERVER -.->|different items| CHK

    CHK --> FILL[Name + email only wired]
    FILL --> CREATE[POST orders/create]
    CREATE --> RZP[Razorpay modal]
    RZP -->|success| VERIFY[POST payments/verify]
    RZP -->|fail| RETRY_UI[Error / retry on order page]
    VERIFY --> SUCCESS[/order-success]

    SUCCESS --> MY_ORDERS[/account/orders]
    MY_ORDERS --> DETAIL[Order detail cancel retry pay]
    DETAIL --> TRACK[/track - placeholder UI]

    AUTH_OK --> REF_PAGE[/referral share link]
    REF_PAGE -->|ref param| REG_BROKEN[/register DISABLED]

    style CHK fill:#fef3c7,stroke:#d97706
    style CART_SERVER fill:#fef3c7,stroke:#d97706
    style REG_BROKEN fill:#fee2e2,stroke:#dc2626
    style TRACK fill:#fee2e2,stroke:#dc2626
    style BROWSE_G fill:#fee2e2,stroke:#dc2626
```

### User flow gaps (annotated)

| Step | Expected | Actual |
|------|----------|--------|
| Discover products | API catalog on home | Mock data on `/` |
| Sign up | `/register` | UI disabled; API works |
| Cart | Single source of truth | Local vs server split |
| Checkout address | Saved to order | Fields not bound |
| Track shipment | Live timeline | Static placeholder |

---

# 5. Admin Flow

```mermaid
flowchart TD
    ASTART([Admin user is_staff]) --> MW{middleware cookie + GET /users/me/}

    MW -->|fail| DENY[Redirect / or /login]
    MW -->|ok| ADMIN_HOME

    subgraph admin_routes [Protected Routes]
        ADMIN_HOME[/admin placeholder metrics]
        DASH[/dashboard live analytics]
        ANALYTICS[/admin/analytics summary API]
        ORD_LIST[/admin/orders list]
        ORD_DET[/admin/orders/id detail]
    end

    DASH --> API1[GET /api/v1/admin/analytics/]
    ANALYTICS --> API2[GET /api/v1/admin/analytics/summary/]
    ORD_LIST --> API3[GET /api/v1/admin/orders/]
    ORD_DET --> API4[GET admin/orders/id/]

    ORD_DET --> ACT{Action}
    ACT --> STATUS[POST status/]
    ACT --> SHIP[POST ship/]
    ACT --> DELIVER[POST deliver/]

    STATUS --> DB[(Order OrderEvent Email)]
    SHIP --> DB
    DELIVER --> DB

    ADMIN_HOME -.->|no API wired| EMPTY[Shows -- placeholders]

    subgraph django_admin [Parallel Path - Django Admin]
        DJANGO[/admin/ Django UI]
        DJANGO --> CRUD[Full model CRUD products users coupons]
    end

    ASTART --> DJANGO

    style ADMIN_HOME fill:#fee2e2,stroke:#dc2626
    style DASH fill:#d1fae5,stroke:#059669
    style ANALYTICS fill:#d1fae5,stroke:#059669
```

### Admin capability split

```mermaid
mindmap
  root((Admin Operations))
    Next_js_UI
      Live analytics dashboard
      Order list filter search
      Status ship deliver
      Shipping address display
      Placeholder /admin home
    Django_Admin
      Product CRUD
      Category inventory images
      User referral management
      Coupon creation
      Bulk order actions
    Missing_UI
      Product management Next.js
      User management Next.js
      Manufacturing Kanban
      Vendor oversight UI
```

---

# 6. Database Relationship Map

```mermaid
erDiagram
    User ||--o{ Order : places
    User ||--o{ Cart : owns
    User ||--o{ CartItem : via_cart
    User ||--o{ Review : writes
    User ||--o{ Wishlist : saves
    User ||--o{ PriceWatch : watches
    User ||--o{ Referral : referrer
    User ||--o| Referral : referred_one
    User ||--o| Vendor : profile
    User ||--o{ Coupon : eligible_for

    Category ||--o{ Product : contains
    Product ||--o{ ProductImage : has
    Product ||--o| Inventory : tracks
    Product ||--o{ Review : receives
    Product ||--o{ FlashSale : promotes
    Product ||--o{ CartItem : in_cart
    Product ||--o{ OrderItem : in_order
    Product ||--o{ Wishlist : wishlisted
    Product ||--o{ PriceWatch : watched
    Product ||--o| VendorProduct : listed_by

    Cart ||--o{ CartItem : contains
    Cart }|--|| User : belongs_to

    Order ||--|{ OrderItem : contains
    Order ||--o| ShippingAddress : has
    Order ||--o{ ShippingEvent : tracks
    Order ||--o{ OrderEvent : audits
    Order ||--o{ EmailEvent : notifies
    Order ||--o{ Payment : paid_via
    Order ||--o| Coupon : applied
    Order ||--o| CouponUsage : records
    Order ||--o{ VendorOrder : splits

    Payment ||--o{ PaymentEvent : immutable_log
    PaymentWebhookEvent ||--|| Payment : dedupes

    Vendor ||--o{ VendorProduct : sells
    Vendor ||--o{ VendorOrder : earns

    Referral }|--|| User : referred_user
    Referral }|--|| User : referrer
```

### Planned entities (not in schema)

```mermaid
erDiagram
    ManufacturingRequest ||--o{ ManufacturingLog : has
    User ||--o{ ManufacturingRequest : submits
    ManufacturingRequest {
        uuid id
        string status
        string file_url
        decimal quoted_price
    }

    StudentProfile {
        uuid user_id
        string student_id_doc
        bool verified
    }

    User ||--o| StudentProfile : has
    User ||--o{ ManufacturingRequest : requests
```

---

# 7. Missing Systems Map

What the **docs/PRD** describe vs what **runs in production code**.

```mermaid
flowchart LR
    subgraph built [Built Systems]
        B1[Ecommerce Core]
        B2[Razorpay Payments]
        B3[JWT Auth]
        B4[Admin Order Ops]
        B5[Wishlist Reviews Referral]
        B6[Vendor APIs]
        B7[Chatbot API]
        B8[Price Watch CMD]
        B9[Redis Cache + CI]
    end

    subgraph partial [Partial / Infra Only]
        P1[Celery worker health task only]
        P2[WebSocket backend no FE]
        P3[Server cart vs client cart]
        P4[Cloudinary URLs only no SDK]
    end

    subgraph missing [Missing Systems]
        M1[Manufacturing pipeline]
        M2[Cloudinary direct upload]
        M3[Vendor portal UI]
        M4[Chatbot UI]
        M5[Flash sale storefront]
        M6[Student verification]
        M7[S3 object storage]
        M8[E2E test suite]
        M9[Celery beat + email tasks]
        M10[Prometheus Sentry]
        M11[Stripe PayPal]
        M12[Legal pages routes]
    end

    built --> partial
    partial --> missing
```

### Missing systems detail

| System | PRD / docs | Code | Frontend | Ops |
|--------|------------|------|----------|-----|
| Manufacturing | ✅ Full state machine | ❌ | ❌ | ❌ |
| Cloudinary | ✅ | ❌ URL only | ❌ | ❌ |
| Unified cart | Implied | ⚠️ Dual | ⚠️ | — |
| Customer registration | ✅ | ✅ API | ❌ UI | — |
| Shipment tracking | ✅ | ✅ model | ❌ UI | — |
| Celery jobs | ✅ | ⚠️ stub | — | ⚠️ worker only |
| Recommendations API | Implied | ⚠️ service | ❌ | — |
| Multi-gateway payments | Optional | ❌ Razorpay only | ✅ | — |

---

# 8. Current vs Planned Architecture

## 8.1 Current architecture (as deployed in repo)

```mermaid
flowchart TB
    subgraph client [Client Tier]
        NEXT[Next.js 14 Vercel or Docker :3000]
    end

    subgraph edge [Edge - Not in repo]
        CDN[CDN - not configured]
    end

    subgraph app [Application Tier]
        DAPHNE[Daphne ASGI :8000]
        CELERY[Celery Worker - health task only]
    end

    subgraph data [Data Tier]
        PG[(PostgreSQL 16)]
        REDIS[(Redis 7)]
        MEDIA[(Local media volume)]
    end

    subgraph external [External Services]
        RZP[Razorpay]
        SMTP[SMTP Email]
        OAI[OpenAI]
    end

    NEXT -->|REST JWT| DAPHNE
    NEXT -->|Checkout.js| RZP
    DAPHNE --> PG
    DAPHNE --> REDIS
    DAPHNE --> MEDIA
    DAPHNE --> RZP
    DAPHNE --> SMTP
    DAPHNE --> OAI
    CELERY --> REDIS
    CELERY --> PG
    RZP -->|webhook| DAPHNE

    style MEDIA fill:#fef3c7,stroke:#d97706
    style CELERY fill:#fef3c7,stroke:#d97706
    style CDN fill:#f3f4f6,stroke:#9ca3af
```

## 8.2 Planned architecture (from PRD / TRD / ROADMAP)

```mermaid
flowchart TB
    subgraph client_p [Client Tier - Planned]
        NEXT_P[Next.js + PWA]
        UPLOAD[Direct Cloudinary Upload]
    end

    subgraph edge_p [Edge - Planned]
        CF[Cloudflare CDN]
        CF --> STATIC[Static assets]
        CF --> MEDIA_CDN[Media CDN]
    end

    subgraph app_p [Application Tier - Planned]
        GUN[Gunicorn + Uvicorn workers]
        CELERY_P[Celery Workers + Beat]
        BEAT[Periodic: price drops abandoned cart]
    end

    subgraph data_p [Data Tier - Planned]
        PG_P[(PostgreSQL + PgBouncer)]
        REDIS_P[(Redis cluster)]
        S3[(S3 / GCS media)]
    end

    subgraph services_p [Domain Services - Planned]
        MFG_SVC[Manufacturing Service]
        VENDOR_UI[Vendor Portal]
        FTS[Postgres FTS Search]
    end

    subgraph observability [Observability - Planned]
        SENTRY[Sentry]
        PROM[Prometheus]
        LOGS[JSON logs to Loki/Datadog]
    end

    NEXT_P --> GUN
    UPLOAD --> MEDIA_CDN
    GUN --> PG_P
    GUN --> REDIS_P
    GUN --> S3
    CELERY_P --> REDIS_P
    BEAT --> CELERY_P
    GUN --> MFG_SVC
    NEXT_P --> VENDOR_UI
    GUN --> FTS
    GUN --> observability
```

## 8.3 Gap diagram: current → planned

```mermaid
flowchart LR
    subgraph now [NOW]
        N1[Modular monolith Django]
        N2[Next storefront partial]
        N3[SQLite or Postgres]
        N4[Local media volume]
        N5[Sync emails]
        N6[Python search]
    end

    subgraph gap [GAP]
        G1[Unify cart + register UI]
        G2[Celery task migration]
        G3[S3 + CDN]
        G4[Manufacturing module]
        G5[Vendor + chatbot FE]
    end

    subgraph target [TARGET]
        T1[Production-grade monolith]
        T2[Full storefront]
        T3[Postgres + pooler]
        T4[Object storage]
        T5[Async notifications]
        T6[FTS or Elasticsearch]
        T7[Vertical manufacturing]
    end

    now --> gap --> target
```

---

# 9. Deployment & Runtime Map

```mermaid
flowchart TB
    subgraph compose [docker-compose.yml]
        DB_SVC[db Postgres]
        REDIS_SVC[redis]
        BE_SVC[backend Daphne migrate]
        CW_SVC[celery_worker]
        FE_SVC[frontend Next standalone]
    end

    subgraph ci [GitHub Actions]
        BE_CI[backend-ci tests migrate check]
        FE_CI[frontend-ci lint build]
    end

    subgraph missing_ops [Not in compose]
        BEAT_SVC[celery beat]
        NGINX[reverse proxy]
        PGB[PgBouncer]
    end

    FE_SVC --> BE_SVC
    BE_SVC --> DB_SVC
    BE_SVC --> REDIS_SVC
    CW_SVC --> REDIS_SVC
    CW_SVC --> DB_SVC

    BE_CI -.-> BE_SVC
    FE_CI -.-> FE_SVC
```

---

# 10. Priority wiring diagram (what to connect first)

Recommended order to collapse the **split-brain** architecture:

```mermaid
flowchart TD
    P1[1 Unify cart FE with orders/carts API]
    P2[2 Wire checkout shipping to ShippingAddress]
    P3[3 Enable register page to users/register]
    P4[4 Home page to products API]
    P5[5 JWT refresh in apiClient]
    P6[6 Celery email tasks + beat]
    P7[7 Track page to shipping_events API]
    P8[8 S3 media]

    P1 --> P2
    P2 --> P3
    P3 --> P4
    P4 --> P5
    P5 --> P6
    P6 --> P7
    P7 --> P8
```

---

## Related files

| Document | Purpose |
|----------|---------|
| `PROJECT_RECOVERY_REPORT.md` | Narrative audit & completion % |
| `API_CONTRACT.md` | Endpoint reference |
| `docs/ROADMAP.md` | Phased engineering tasks |
| `docs/AUDIT_REPORT.md` | Security & architecture audit |

---

*End of Visual Development Map*
