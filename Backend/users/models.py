import uuid
from secrets import token_hex

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import IntegrityError
from django.db import models
from django.utils import timezone

MAX_CODE_GENERATION_ATTEMPTS = 5


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("role", User.Role.ADMIN)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True")

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        STUDENT = "student", "Student"
        VENDOR = "vendor", "Vendor"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STUDENT)
    referral_owner_code = models.CharField(max_length=20, unique=True, db_index=True, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    def save(self, *args, **kwargs):
        if self.referral_owner_code:
            return super().save(*args, **kwargs)
        for _ in range(MAX_CODE_GENERATION_ATTEMPTS):
            self.referral_owner_code = token_hex(5).upper()
            try:
                return super().save(*args, **kwargs)
            except IntegrityError:
                continue
        raise IntegrityError("Unable to generate unique referral owner code.")

    def __str__(self):
        return self.email


class Referral(models.Model):
    referrer = models.ForeignKey(User, on_delete=models.PROTECT, related_name="referrals_made")
    referred_user = models.OneToOneField(User, on_delete=models.PROTECT, related_name="referral_record")
    referral_code = models.CharField(max_length=20, unique=True, db_index=True, blank=True)
    reward_issued = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["referrer", "reward_issued"]),
        ]

    def save(self, *args, **kwargs):
        if self.referral_code:
            return super().save(*args, **kwargs)
        for _ in range(MAX_CODE_GENERATION_ATTEMPTS):
            self.referral_code = token_hex(5).upper()
            try:
                return super().save(*args, **kwargs)
            except IntegrityError:
                continue
        raise IntegrityError("Unable to generate unique referral code.")


class AuthEvent(models.Model):
    class EventType(models.TextChoices):
        TOKEN_REFRESH_ATTEMPT = "token_refresh_attempt", "Token Refresh Attempt"
        TOKEN_REFRESH_FAILED = "token_refresh_failed", "Token Refresh Failed"
        TOKEN_REFRESH_SUCCESS = "token_refresh_success", "Token Refresh Success"
        LOGIN_ATTEMPT = "login_attempt", "Login Attempt"
        LOGIN_FAILED = "login_failed", "Login Failed"
        LOGIN_SUCCESS = "login_success", "Login Success"

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="auth_events")
    event_type = models.CharField(max_length=40, choices=EventType.choices)
    request_id = models.CharField(max_length=100, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["event_type", "created_at"]),
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["request_id", "created_at"]),
        ]
