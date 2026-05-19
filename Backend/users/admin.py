from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import Referral, User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    ordering = ("-created_at",)
    list_display = ("email", "name", "role", "referral_owner_code", "is_staff", "is_active", "created_at")
    list_filter = ("role", "is_staff", "is_active")
    search_fields = ("email", "name", "referral_owner_code")
    readonly_fields = ("created_at",)
    list_select_related = ()
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("name", "role")}),
        (
            "Permissions",
            {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        ("Important dates", {"fields": ("last_login", "created_at")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "name", "role", "referral_owner_code", "password1", "password2", "is_staff", "is_active"),
            },
        ),
    )


@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display = ("id", "referrer", "referred_user", "referral_code", "reward_issued", "created_at")
    list_filter = ("reward_issued", "created_at")
    search_fields = ("referrer__email", "referred_user__email", "referral_code")
    list_select_related = ("referrer", "referred_user")
