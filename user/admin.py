from .models import User, UserInfo, OTP, MessageLog, Address, MulticardConfig, Referral,UserShareInfo
from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _


@admin.register(MulticardConfig)
class MulticardConfigAdmin(admin.ModelAdmin):
    list_display = ("id", "application_id", "secret_key", "store_id")


def avatar_preview(obj):
    if obj.avatar:
        return format_html(
            '<img src="{}" style="height: 50px; width: 50px; object-fit: cover; border-radius: 5px;" />',
            obj.avatar.url,
        )
    return "-"


avatar_preview.short_description = "Avatar"


class UserInfoInline(admin.StackedInline):
    model = UserInfo
    extra = 0
    readonly_fields = [avatar_preview]
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "gender",
                    "birth_date",
                    "address",
                    "avatar",
                    "language",
                    avatar_preview,
                ),
            },
        ),
    )


@admin.register(User)
class CustomUserAdmin(admin.ModelAdmin):
    list_per_page = 500
    list_display = (
        "phone",
        "role",
        "is_active",
        "created_at",
        "has_info_display",
        "odoo_id",
    )
    list_filter = ("role", "is_active", "is_staff")
    search_fields = ("phone", "odoo_id")
    ordering = ("-created_at",)
    inlines = [UserInfoInline]

    fieldsets = (
        (_("User Info"), {"fields": ("phone", "role", "odoo_id", "send_odoo")}),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (_("Dates"), {"fields": ("created_at", "updated_at")}),
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    def has_info_display(self, obj):
        return obj.has_info

    has_info_display.boolean = True
    has_info_display.short_description = _("Has Info")


@admin.register(UserInfo)
class UserInfoAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "first_name",
        "last_name",
        "gender",
        "birth_date",
        "language",
        "referral_link",
        "referral_count",
        avatar_preview,
    )
    list_filter = ("gender", "language")
    search_fields = ("first_name", "last_name", "user__phone")
    readonly_fields = [avatar_preview]
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "user",
                    "first_name",
                    "last_name",
                    "gender",
                    "birth_date",
                    "address",
                    "language",
                    "avatar",
                    avatar_preview,
                    "referral_link",
                    "referral_count",
                ),
            },
        ),
    )


@admin.register(OTP)
class OTPAdmin(admin.ModelAdmin):
    list_display = ("id", "phone", "code", "is_used", "expired_at", "created_at")
    search_fields = ("phone",)
    ordering = ("created_at",)


@admin.register(MessageLog)
class MessageLogAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "recipient",
        "message_type",
        "content_type",
        "sent_at",
        "object_id",
        "context",
        "content",
        "status",
        "error_details",
    )
    search_fields = (
        "recipient",
        "content",
        "status",
    )
    list_filter = ("status", "recipient", "content_type")
    ordering = ("-id",)


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "user",
        "additional",
        "yandex_link",
        "building",
        "floor",
        "demophone_code",
        "is_main",
    ]
    search_fields = ["additional"]


@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display = ("referrer", "referred", "created_at")
    search_fields = ("referrer__phone", "referred__phone")
    list_filter = ("created_at",)
    ordering = ("-created_at",)
    
@admin.register(UserShareInfo)
class UserShareInfoAdmin(admin.ModelAdmin):
    list_display = ("user", "unique_code", "phone_number_allowed")
    search_fields = ("user__phone", "unique_code")
    list_filter = ("phone_number_allowed",)