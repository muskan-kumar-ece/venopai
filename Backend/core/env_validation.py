from dataclasses import dataclass

from django.conf import settings


@dataclass
class ValidationIssue:
    level: str
    key: str
    message: str


def validate_environment() -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if not settings.SECRET_KEY:
        issues.append(ValidationIssue("error", "SECRET_KEY", "SECRET_KEY is required"))
    if settings.DJANGO_ENV == "prod":
        if settings.SECRET_KEY and len(settings.SECRET_KEY) < 32:
            issues.append(ValidationIssue("error", "SECRET_KEY", "SECRET_KEY must be at least 32 characters"))
        if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
            issues.append(ValidationIssue("warning", "RAZORPAY", "Razorpay keys are not configured"))
        if not settings.CELERY_BROKER_URL:
            issues.append(ValidationIssue("warning", "CELERY_BROKER_URL", "Queue broker is not configured"))
        if not settings.CACHE_REDIS_URL:
            issues.append(ValidationIssue("warning", "CACHE_REDIS_URL", "Redis cache is not configured"))
        if not settings.SENTRY_DSN:
            issues.append(ValidationIssue("warning", "SENTRY_DSN", "Sentry DSN is not configured"))
        if settings.MEDIA_STORAGE_BACKEND != "cloudinary":
            issues.append(ValidationIssue("warning", "MEDIA_STORAGE_BACKEND", "Production media should use Cloudinary"))
        if settings.MEDIA_STORAGE_BACKEND == "cloudinary":
            missing = [
                key
                for key in ("CLOUDINARY_CLOUD_NAME", "CLOUDINARY_API_KEY", "CLOUDINARY_API_SECRET")
                if not getattr(settings, key)
            ]
            if missing:
                issues.append(ValidationIssue("error", "CLOUDINARY", f"Missing Cloudinary settings: {', '.join(missing)}"))
        if not settings.ALLOWED_HOSTS or settings.ALLOWED_HOSTS == ["localhost", "127.0.0.1"]:
            issues.append(ValidationIssue("error", "ALLOWED_HOSTS", "ALLOWED_HOSTS must be explicitly configured"))
    return issues
