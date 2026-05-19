from datetime import timedelta
from pathlib import Path

from decouple import Csv, config
from django.core.management.utils import get_random_secret_key
import sentry_sdk

BASE_DIR = Path(__file__).resolve().parent.parent.parent

DJANGO_ENV = config("DJANGO_ENV", default="dev")
SECRET_KEY = config("SECRET_KEY", default=get_random_secret_key())
DEBUG = config("DEBUG", default=False, cast=bool)
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv())
ADMIN_URL_PATH = config("ADMIN_URL_PATH", default="admin/")

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "corsheaders",
    "rest_framework",
    "django_filters",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "channels",
    "drf_spectacular",
]

LOCAL_APPS = [
    "users",
    "products",
    "orders",
    "payments",
    "apps.wishlist",
    "apps.recommendations",
    "apps.chatbot",
    "apps.price_watch",
    "vendors",
    "adminpanel",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.gzip.GZipMiddleware",
    "core.middleware.RequestIDMiddleware",
    "core.security_middleware.SecurityHeadersMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "core.wsgi.application"
ASGI_APPLICATION = "core.asgi.application"

CHANNEL_REDIS_URL = config("CHANNEL_REDIS_URL", default="")
if CHANNEL_REDIS_URL:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {
                "hosts": [CHANNEL_REDIS_URL],
            },
        }
    }
else:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
        }
    }

# Cache — use Redis when available, fall back to in-memory for local dev.
CACHE_REDIS_URL = config("CACHE_REDIS_URL", default="")
if CACHE_REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": CACHE_REDIS_URL,
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
                "SOCKET_CONNECT_TIMEOUT": 5,
                "SOCKET_TIMEOUT": 5,
            },
            "KEY_PREFIX": "ecommerce",
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    }

# Default cache TTLs (seconds) — can be overridden per view.
CACHE_TTL_PRODUCT_LIST = config("CACHE_TTL_PRODUCT_LIST", default=300, cast=int)   # 5 min
CACHE_TTL_ANALYTICS = config("CACHE_TTL_ANALYTICS", default=600, cast=int)         # 10 min
CACHE_TTL_HEALTH = config("CACHE_TTL_HEALTH", default=10, cast=int)

REDIS_URL = config("REDIS_URL", default="")
if not REDIS_URL:
    REDIS_URL = CACHE_REDIS_URL

CELERY_BROKER_URL = config("CELERY_BROKER_URL", default=REDIS_URL)
CELERY_RESULT_BACKEND = config("CELERY_RESULT_BACKEND", default=CELERY_BROKER_URL)
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = config("CELERY_TASK_TIME_LIMIT", default=300, cast=int)
CELERY_TASK_SOFT_TIME_LIMIT = config("CELERY_TASK_SOFT_TIME_LIMIT", default=240, cast=int)
CELERY_RESULT_EXPIRES = config("CELERY_RESULT_EXPIRES", default=3600, cast=int)

if config("DB_NAME", default=""):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": config("DB_NAME"),
            "USER": config("DB_USER", default="postgres"),
            "PASSWORD": config("DB_PASSWORD", default=""),
            "HOST": config("DB_HOST", default="localhost"),
            "PORT": config("DB_PORT", default="5432"),
            "CONN_MAX_AGE": config("DB_CONN_MAX_AGE", default=60, cast=int),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"
MEDIA_STORAGE_BACKEND = config("MEDIA_STORAGE_BACKEND", default="local")

CLOUDINARY_CLOUD_NAME = config("CLOUDINARY_CLOUD_NAME", default="")
CLOUDINARY_API_KEY = config("CLOUDINARY_API_KEY", default="")
CLOUDINARY_API_SECRET = config("CLOUDINARY_API_SECRET", default="")
CLOUDINARY_SECURE = config("CLOUDINARY_SECURE", default=True, cast=bool)
CLOUDINARY_PRODUCT_FOLDER = config("CLOUDINARY_PRODUCT_FOLDER", default="venopai/products")
CLOUDINARY_DELIVERY_HOST = (
    f"res.cloudinary.com/{CLOUDINARY_CLOUD_NAME}"
    if CLOUDINARY_CLOUD_NAME
    else ""
)

PRODUCT_IMAGE_MAX_UPLOAD_MB = config("PRODUCT_IMAGE_MAX_UPLOAD_MB", default=8, cast=int)
PRODUCT_IMAGE_ALLOWED_CONTENT_TYPES = config(
    "PRODUCT_IMAGE_ALLOWED_CONTENT_TYPES",
    default="image/jpeg,image/png,image/webp",
    cast=Csv(),
)
PRODUCT_IMAGE_ALLOWED_HOSTS = config(
    "PRODUCT_IMAGE_ALLOWED_HOSTS",
    default="",
    cast=Csv(),
)

if MEDIA_STORAGE_BACKEND == "cloudinary":
    STORAGES = {
        "default": {
            "BACKEND": "core.media_storage.CloudinaryMediaStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }

if CLOUDINARY_CLOUD_NAME and CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET:
    try:
        import cloudinary

        cloudinary.config(
            cloud_name=CLOUDINARY_CLOUD_NAME,
            api_key=CLOUDINARY_API_KEY,
            api_secret=CLOUDINARY_API_SECRET,
            secure=CLOUDINARY_SECURE,
        )
    except ImportError:
        pass

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "users.User"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "core.exceptions.api_exception_handler",
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": config("THROTTLE_RATE_ANON", default="100/hour"),
        "user": config("THROTTLE_RATE_USER", default="2000/hour"),
        "auth": config("THROTTLE_RATE_AUTH", default="10/minute"),
        "register": config("THROTTLE_RATE_REGISTER", default="5/minute"),
        "order_create": config("THROTTLE_RATE_ORDER_CREATE", default="30/hour"),
        "payments": config("THROTTLE_RATE_PAYMENTS", default="60/hour"),
        "payments_webhook": config("THROTTLE_RATE_PAYMENTS_WEBHOOK", default="300/hour"),
        "reviews": config("THROTTLE_RATE_REVIEWS", default="10/hour"),
        "chatbot": config("THROTTLE_RATE_CHATBOT", default="30/hour"),
        "wishlist_mutations": config("THROTTLE_RATE_WISHLIST_MUTATIONS", default="60/hour"),
        "price_watch": config("THROTTLE_RATE_PRICE_WATCH", default="60/hour"),
        "admin": config("THROTTLE_RATE_ADMIN", default="120/hour"),
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=config("JWT_ACCESS_MINUTES", default=15, cast=int)),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=config("JWT_REFRESH_DAYS", default=7, cast=int)),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default="http://localhost:3000",
    cast=Csv(),
)

CSRF_TRUSTED_ORIGINS = config(
    "CSRF_TRUSTED_ORIGINS",
    default="http://localhost:3000",
    cast=Csv(),
)
FRONTEND_APP_URL = config("FRONTEND_APP_URL", default="http://localhost:3000")

SESSION_COOKIE_SECURE = config("SESSION_COOKIE_SECURE", default=DJANGO_ENV != "dev", cast=bool)
CSRF_COOKIE_SECURE = config("CSRF_COOKIE_SECURE", default=DJANGO_ENV != "dev", cast=bool)
SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=DJANGO_ENV == "prod", cast=bool)
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = config("CSRF_COOKIE_HTTPONLY", default=False, cast=bool)
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
CSRF_COOKIE_SAMESITE = config("CSRF_COOKIE_SAMESITE", default="Lax")
SESSION_COOKIE_SAMESITE = config("SESSION_COOKIE_SAMESITE", default="Lax")
CONTENT_SECURITY_POLICY = config(
    "CONTENT_SECURITY_POLICY",
    default="default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; img-src 'self' data: https:; connect-src 'self' https:; frame-src https://api.razorpay.com https://checkout.razorpay.com;",
)

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = config("EMAIL_HOST", default="localhost")
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
EMAIL_HOST_USER = config("EMAIL_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_PASSWORD", default="")
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="no-reply@venopai.com")
SUPPORT_EMAIL = config("SUPPORT_EMAIL", default="support@venopai.com")

RAZORPAY_KEY_ID = config("RAZORPAY_KEY_ID", default="")
RAZORPAY_KEY_SECRET = config("RAZORPAY_KEY_SECRET", default="")
RAZORPAY_WEBHOOK_SECRET = config("RAZORPAY_WEBHOOK_SECRET", default="")
RAZORPAY_API_BASE_URL = config("RAZORPAY_API_BASE_URL", default="https://api.razorpay.com/v1")
OPENAI_API_KEY = config("OPENAI_API_KEY", default="")
OPENAI_MODEL = config("OPENAI_MODEL", default="gpt-4o-mini")

LOG_LEVEL = config("LOG_LEVEL", default="INFO")
# Set LOG_FORMAT=json in production to emit machine-parseable JSON log lines
# (e.g. for ingestion by CloudWatch, Datadog, Loki).
# Any other value (including the default "text") uses a human-readable format.
LOG_FORMAT = config("LOG_FORMAT", default="json" if DJANGO_ENV == "prod" else "text")
SENTRY_DSN = config("SENTRY_DSN", default="")
SENTRY_TRACES_SAMPLE_RATE = config("SENTRY_TRACES_SAMPLE_RATE", default=0.0, cast=float)
SENTRY_PROFILES_SAMPLE_RATE = config("SENTRY_PROFILES_SAMPLE_RATE", default=0.0, cast=float)
STARTUP_STRICT_VALIDATION = config("STARTUP_STRICT_VALIDATION", default=False, cast=bool)

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
            # request_id is injected by RequestIDFilter; falls back to "-" when
            # logging happens outside a request context (e.g. management commands).
            "format": "%(asctime)s %(levelname)s [%(request_id)s] %(name)s %(message)s",
        },
        "json": {
            # Structured JSON formatter – enabled when LOG_FORMAT=json.
            # Each log line is a single JSON object, making it trivial to
            # parse, filter, and alert on in log aggregation platforms.
            "()": "core.log_filters.JsonFormatter",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            # Use JSON formatter when LOG_FORMAT=json, otherwise human-readable text.
            "formatter": "json" if LOG_FORMAT == "json" else "verbose",
            "filters": ["request_id"],
        }
    },
    "root": {"handlers": ["console"], "level": LOG_LEVEL},
}

if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=DJANGO_ENV,
        traces_sample_rate=SENTRY_TRACES_SAMPLE_RATE,
        profiles_sample_rate=SENTRY_PROFILES_SAMPLE_RATE,
        send_default_pii=False,
    )

# ---------------------------------------------------------------------------
# drf-spectacular – auto-generated OpenAPI schema
# ---------------------------------------------------------------------------
SPECTACULAR_SETTINGS = {
    "TITLE": "Ecommerce API",
    "DESCRIPTION": (
        "REST API for the Venopai ecommerce platform. "
        "All endpoints under /api/v1/ require a Bearer JWT unless marked public."
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SCHEMA_PATH_PREFIX": r"/api/v1/",
}
