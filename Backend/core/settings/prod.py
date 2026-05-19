from decouple import config

from .base import *

DEBUG = False
LOG_FORMAT = config("LOG_FORMAT", default="json")
SECRET_KEY = config("SECRET_KEY")

SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=True, cast=bool)
# Required when Django runs behind a load balancer or reverse proxy.
# Without this, SECURE_SSL_REDIRECT causes an infinite redirect loop because
# Django cannot see the original HTTPS scheme — it only sees HTTP from the proxy.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = config("SECURE_HSTS_SECONDS", default=31536000, cast=int)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
X_FRAME_OPTIONS = "DENY"
