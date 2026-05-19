# Logging Audit — Django Backend

**Platform:** Venopai Ecommerce  
**Audit Date:** March 2026  
**Scope:** Django backend (`Backend/`)  

---

## SECTION 1 — Current Logging Configuration

### 1.1 Settings (`core/settings/base.py`)

```python
LOG_LEVEL = config("LOG_LEVEL", default="INFO")
LOG_FORMAT = config("LOG_FORMAT", default="text")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "request_id": {
            "()": "core.log_filters.RequestIDFilter",
        },
    },
    "formatters": {
        "verbose": {
            "format": "%(asctime)s %(levelname)s [%(request_id)s] %(name)s %(message)s",
        },
        "json": {
            "()": "core.log_filters.JsonFormatter",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json" if LOG_FORMAT == "json" else "verbose",
            "filters": ["request_id"],
        }
    },
    "root": {"handlers": ["console"], "level": LOG_LEVEL},
}
```

**Key properties:**

| Property | Value |
|----------|-------|
| Handler | Single `StreamHandler` → stdout |
| Default level | `INFO` (configurable via `LOG_LEVEL` env var) |
| Format | Human-readable text (default), or JSON when `LOG_FORMAT=json` |
| Filter | `RequestIDFilter` — injects `request_id` per log line |
| Persistent log file | ❌ None (intentional for containerised deployment; log collection is the platform's responsibility) |
| Log rotation | ❌ None (delegate to container runtime / log agent) |

### 1.2 `core/log_filters.py`

Two classes are defined:

| Class | Purpose |
|-------|---------|
| `RequestIDFilter` | Reads `request_id` from thread-local (set by `RequestIDMiddleware`) and attaches it to every `LogRecord`. Falls back to `"-"` outside request context. |
| `JsonFormatter` | Emits a single JSON object per log line with fields: `timestamp`, `level`, `request_id`, `logger`, `message`, `exc_info` (when present). Activated when `LOG_FORMAT=json`. |

### 1.3 `core/middleware.py` — `RequestIDMiddleware`

On every HTTP request:
1. Reads `X-Request-ID` header from the incoming request (pass-through from load-balancer), or generates a new UUID4.
2. Writes the ID to `request.request_id`.
3. Writes the ID to thread-local via `core.log_filters.set_request_id()`.
4. Sets `X-Request-ID` on the response.

This ensures every log line emitted during a request carries the same trace ID.

### 1.4 Module Coverage — Before This Audit

| Module | Has `logger`? | Logged Failures Before? |
|--------|--------------|-------------------------|
| `payments/views.py` | ✅ | ✅ Razorpay, signature, webhook |
| `payments/services.py` | ✅ | ❌ `RazorpayIntegrationError` was re-raised silently |
| `apps/chatbot/services.py` | ✅ | ✅ OpenAI failures |
| `orders/notifications.py` | ❌ | ❌ SMTP failures swallowed silently |
| `apps/price_watch/notifications.py` | ❌ | ❌ SMTP failures swallowed silently |
| `core/health.py` | ❌ | ❌ DB/cache probe failures not logged |
| `core/middleware.py` | ✅ | N/A |
| All other modules | ❌ | N/A (no failure paths requiring explicit logging) |

---

## SECTION 2 — Problems Found

### Problem 1 — SMTP Failures Were Completely Silent ❌ (FIXED)

**Files:** `orders/notifications.py`, `apps/price_watch/notifications.py`

Both modules caught `(SMTPException, BadHeaderError, OSError)` and returned `False` without logging anything. This meant:

- A mis-configured SMTP server would silently drop all order confirmation emails.
- A production outage where no order email was ever sent would be invisible in logs.
- Support would only discover the problem when customers complained.

```python
# BEFORE (orders/notifications.py:70)
except (SMTPException, BadHeaderError, OSError):
    email_event.status = EmailEvent.Status.FAILED
    email_event.save(...)
    return False  # ← no logger call; failure is invisible
```

```python
# AFTER
except (SMTPException, BadHeaderError, OSError) as exc:
    logger.error(
        "Failed to send order email type=%s order_id=%s: %s",
        email_type, order.id, exc,
    )
    ...
```

**Impact:** `CRITICAL` — email delivery outages were completely invisible.

---

### Problem 2 — Razorpay Network Errors Were Not Logged Before Raising ❌ (FIXED)

**File:** `payments/services.py:186`

`create_razorpay_order()` caught network/timeout exceptions and immediately re-raised as `RazorpayIntegrationError` without logging. The caller (`payments/views.py`) did log the resulting exception at `ERROR`, but that log line contained the view-level context only — not the low-level root cause (which URL was called, what the underlying error was, what receipt was being processed).

```python
# BEFORE
except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
    raise RazorpayIntegrationError("Failed to create Razorpay order") from exc
```

```python
# AFTER
except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
    logger.error("Razorpay create-order API call failed receipt=%s: %s", receipt, exc)
    raise RazorpayIntegrationError("Failed to create Razorpay order") from exc
```

**Impact:** `HIGH` — diagnosing checkout failures required correlating two separate log sources with no explicit linkage.

---

### Problem 3 — Health Check Dependency Failures Were Not Logged ❌ (FIXED)

**File:** `core/health.py`

When the database or Redis probe failed, the health endpoint returned a structured error response but did not emit any log line. A `503` response from the health check would not trigger a log-based alert in platforms that watch for `ERROR`-level log lines.

```python
# BEFORE
except OperationalError as exc:
    checks["database"] = f"error: {exc}"
    http_status = 503
```

```python
# AFTER
except OperationalError as exc:
    checks["database"] = f"error: {exc}"
    http_status = 503
    logger.error("Health check: database probe failed: %s", exc)
```

**Impact:** `MEDIUM` — log-based alerting would miss health check degradation events.

---

### Problem 4 — No Structured (JSON) Log Format for Production ❌ (FIXED)

**File:** `core/settings/base.py`, `core/log_filters.py`

All log lines were plain human-readable text. This is fine for local development but is problematic in production because:

- Log aggregation platforms (CloudWatch, Datadog, Loki, Splunk) cannot reliably parse free-form text.
- Filtering by field (e.g. "show all ERROR logs for request_id=X") requires fragile regex instead of a simple JSON path query.
- Multi-line stack traces in `exc_info` break line-oriented log parsers.

**Impact:** `HIGH` for any production environment using a log aggregation platform.

---

### Problem 5 — No Slow-Query or Django Request Logging ⚠️ (Recommended, not implemented)

Neither `django.request` nor `django.db.backends` are configured as named loggers with explicit levels. This means:

- HTTP 500 errors generate Django's built-in `ERROR` log via the root logger but without being easily filterable by logger name.
- N+1 queries added by new code go undetected until they cause latency spikes.

**Recommendation:** In `settings/dev.py`, add:

```python
LOGGING["loggers"] = {
    "django.db.backends": {
        "level": "DEBUG",
        "handlers": ["console"],
        "propagate": False,
    },
    "django.request": {
        "level": "WARNING",
        "handlers": ["console"],
        "propagate": False,
    },
}
```

This is a development-only concern; do not enable `django.db.backends` DEBUG in production as it logs every SQL query.

---

### Problem 6 — Redis Failures in Cache Operations Have No Application-Level Log ⚠️ (Low severity)

When `django-redis` fails (e.g. `CACHE_REDIS_URL` is set but Redis is unreachable), Django raises `ConnectionError`. Views using `@cache_page` or explicit `cache.get/set` calls would raise this error and it would be captured by Django's 500 error handler — but the `ERROR` log line would come from `django.request`, not from the application code.

For explicit cache calls in application code (e.g. `products/views.py`), a `try/except` + `logger.warning` is recommended:

```python
try:
    cached = cache.get(cache_key)
except Exception:
    logger.warning("Cache unavailable for key=%s, falling back to DB", cache_key)
    cached = None
```

---

## SECTION 3 — Recommended Production Logging Setup

### 3.1 Environment Variables

```bash
# Human-readable (development / when viewing logs in a terminal)
LOG_LEVEL=DEBUG
LOG_FORMAT=text

# Structured JSON (production / when ingesting into a log platform)
LOG_LEVEL=INFO
LOG_FORMAT=json
```

### 3.2 Sample Text Log Output

```
2026-03-08T06:00:00.123456 ERROR [b1c2d3e4-5678-90ab-cdef-0123456789ab] orders.notifications Failed to send order email type=order_confirmed order_id=42: [Errno 111] Connection refused
```

### 3.3 Sample JSON Log Output (`LOG_FORMAT=json`)

```json
{
  "timestamp": "2026-03-08T06:00:00.123456+00:00",
  "level": "ERROR",
  "request_id": "b1c2d3e4-5678-90ab-cdef-0123456789ab",
  "logger": "orders.notifications",
  "message": "Failed to send order email type=order_confirmed order_id=42: [Errno 111] Connection refused"
}
```

With exception:

```json
{
  "timestamp": "2026-03-08T06:00:00.456789+00:00",
  "level": "ERROR",
  "request_id": "b1c2d3e4-5678-90ab-cdef-0123456789ab",
  "logger": "payments.services",
  "message": "Razorpay create-order API call failed receipt=order-42: timed out",
  "exc_info": "Traceback (most recent call last):\n  File \"...\"\nTimeoutError: timed out"
}
```

### 3.4 Full Coverage Map — After This Audit

| Failure Type | Logger | Level | Field Coverage |
|-------------|--------|-------|----------------|
| SMTP — order email | `orders.notifications` | `ERROR` | `email_type`, `order_id`, exception message |
| SMTP — abandoned cart | `orders.notifications` | `ERROR` | `cart_id`, `user_id`, exception message |
| SMTP — price drop alert | `apps.price_watch.notifications` | `ERROR` | `product_id`, `user_id`, exception message |
| Razorpay network error | `payments.services` | `ERROR` | `receipt`, exception message |
| Razorpay webhook secret missing | `payments.views` | `ERROR` | N/A |
| Razorpay signature mismatch | `payments.views` | `WARNING` | `order_id` |
| Razorpay duplicate payment | `payments.views` | `WARNING` | `razorpay_payment_id` |
| Razorpay payment failure | `payments.views` | `ERROR` | `order_id` |
| OpenAI API error | `apps.chatbot.services` | `WARNING` | exception message |
| DB probe failure | `core.health` | `ERROR` | exception message |
| Redis probe failure | `core.health` | `ERROR` | exception message |
| Order creation error | `payments.views` | `exception` | (full stack trace) |
| Payment retry error | `payments.views` | `exception` | (full stack trace) |

### 3.5 Log Correlation Flow

```
HTTP Request → RequestIDMiddleware → sets X-Request-ID + thread-local
                     │
                     ▼
          RequestIDFilter.filter()  ←──────────────────────┐
                     │                                      │
                     ▼                                      │
         Every logger.xxx() call                  Every logger.xxx() call
         during this request                      in background tasks (no request_id)
         receives request_id="<uuid>"             receives request_id="-"
                     │
                     ▼
          Console handler → stdout
          (text or JSON format)
                     │
                     ▼
         Container runtime collects stdout
                     │
                     ▼
         Log aggregation platform
         (CloudWatch / Datadog / Loki)
```

---

## SECTION 4 — Exact Code Changes Made

### 4.1 `Backend/orders/notifications.py`

**Added:** module-level logger; `exc` variable binding and `logger.error()` call in two except blocks.

```diff
+import logging
 from smtplib import SMTPException
 ...
+logger = logging.getLogger(__name__)
 ...
-        except (SMTPException, BadHeaderError, OSError):
+        except (SMTPException, BadHeaderError, OSError) as exc:
+            logger.error(
+                "Failed to send order email type=%s order_id=%s: %s",
+                email_type,
+                order.id,
+                exc,
+            )
             email_event.status = EmailEvent.Status.FAILED
             ...
-    except (SMTPException, BadHeaderError, OSError):
+    except (SMTPException, BadHeaderError, OSError) as exc:
+        logger.error(
+            "Failed to send abandoned cart email cart_id=%s user_id=%s: %s",
+            cart.id,
+            cart.user_id,
+            exc,
+        )
         return False
```

### 4.2 `Backend/apps/price_watch/notifications.py`

**Added:** module-level logger; `exc` variable binding and `logger.error()` call.

```diff
+import logging
 from smtplib import SMTPException
 ...
+logger = logging.getLogger(__name__)
 ...
-    except (SMTPException, BadHeaderError, OSError):
+    except (SMTPException, BadHeaderError, OSError) as exc:
+        logger.error(
+            "Failed to send price drop email product_id=%s user_id=%s: %s",
+            price_watch.product_id,
+            price_watch.user_id,
+            exc,
+        )
         return False
```

### 4.3 `Backend/payments/services.py`

**Added:** `logger.error()` before re-raising `RazorpayIntegrationError`.

```diff
     except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
+        logger.error("Razorpay create-order API call failed receipt=%s: %s", receipt, exc)
         raise RazorpayIntegrationError("Failed to create Razorpay order") from exc
```

### 4.4 `Backend/core/health.py`

**Added:** module-level logger; `logger.error()` calls in the DB and Redis except blocks.

```diff
+import logging
 import time
 ...
+logger = logging.getLogger(__name__)
 ...
         except OperationalError as exc:
             checks["database"] = f"error: {exc}"
             http_status = 503
+            logger.error("Health check: database probe failed: %s", exc)
 ...
             except Exception as exc:
                 checks["cache"] = f"error: {exc}"
                 http_status = 503
+                logger.error("Health check: cache probe failed: %s", exc)
```

### 4.5 `Backend/core/log_filters.py`

**Added:** `JsonFormatter` class — emits one JSON object per log line.

```python
class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp":  self.formatTime(record, datefmt="%Y-%m-%dT%H:%M:%S.%f"),
            "level":      record.levelname,
            "request_id": getattr(record, "request_id", "-"),
            "logger":     record.name,
            "message":    record.getMessage(),
        }
        if record.exc_info:
            payload["exc_info"] = "".join(traceback.format_exception(*record.exc_info)).rstrip()
        return json.dumps(payload, ensure_ascii=False)
```

### 4.6 `Backend/core/settings/base.py`

**Added:** `LOG_FORMAT` env var; `"json"` formatter entry; conditional formatter selection in handler.

```diff
 LOG_LEVEL = config("LOG_LEVEL", default="INFO")
+LOG_FORMAT = config("LOG_FORMAT", default="text")
 LOGGING = {
     ...
     "formatters": {
         "verbose": {
             "format": "%(asctime)s %(levelname)s [%(request_id)s] %(name)s %(message)s",
         },
+        "json": {
+            "()": "core.log_filters.JsonFormatter",
+        },
     },
     "handlers": {
         "console": {
-            "formatter": "verbose",
+            "formatter": "json" if LOG_FORMAT == "json" else "verbose",
             ...
         }
     },
 }
```

### 4.7 `Backend/core/tests_logging.py` (new)

**Added:** 15 unit tests covering:
- `RequestIDFilter` — thread-local injection, default fallback, always-True return
- `JsonFormatter` — valid JSON output, required fields, level name, request_id, message, exc_info present/absent
- `orders/notifications.py` — `send_order_email` and `send_abandoned_cart_email` log SMTP failures
- `apps/price_watch/notifications.py` — `send_price_drop_email` logs SMTP failures
- `payments/services.py` — `create_razorpay_order` logs Razorpay network errors

### 4.8 `Backend/.env.example`

**Added:** `LOG_FORMAT` variable with documentation comment.

```diff
 LOG_LEVEL=INFO
+# Set LOG_FORMAT=json in production for structured/machine-parseable log lines
+LOG_FORMAT=text
```
