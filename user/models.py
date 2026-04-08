import logging
import os, uuid
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from uuid import uuid4
from django.db import models, transaction
from app.models.log_connection import SyncSoftDeleteMixin
from app.utils.utils import OdooSync
from app.models.qr_codes import QRCode
logger = logging.getLogger(__name__)


def avatar_upload_to(instance, filename):
    exc = filename.split(".")[-1]
    filename = f"{uuid4()}.{exc}"
    return os.path.join("avatars", filename)


# Custom User Manager
class UserManager(BaseUserManager):
    def create_user(self, phone, password=None, **extra_fields):
        if not phone:
            raise ValueError(_("The phone field must be set"))

        user = self.model(phone=phone, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, phone, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True"))

        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True"))

        return self.create_user(phone, password, **extra_fields)


# User Model
class User(AbstractBaseUser, PermissionsMixin, SyncSoftDeleteMixin):
    class UserRole(models.TextChoices):
        REGULAR = "REGULAR", _("Regular User")
        ADMIN = "ADMIN", _("Admin")

    odoo_id = models.CharField(max_length=255, null=True, blank=True)
    send_odoo = models.BooleanField(default=True)
    phone_regex = RegexValidator(
        regex=r"^(\+998|998)\d{9}$",
        message="Phone number must be in correct format: +998XXXXXXXXX or 998XXXXXXXXX",
    )
    phone = models.CharField(validators=[phone_regex], max_length=20, unique=True)

    role = models.CharField(
        max_length=10, choices=UserRole.choices, default=UserRole.REGULAR
    )
    password = models.CharField(max_length=128, blank=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    groups = models.ManyToManyField(
        "auth.Group", related_name="custom_user_groups", blank=True
    )
    user_permissions = models.ManyToManyField(
        "auth.Permission", related_name="custom_user_permissions", blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        db_table = "users"

    @property
    def has_info(self):
        return hasattr(self, "info")

    def get_short_name(self):
        """Return the short name for the user."""
        return self.phone
    
    def get_full_name(self):
        name = self.info.first_name if self.info and self.info.first_name else "Public"
        last = self.info.last_name if self.info and self.info.last_name else "User"
        return f"{name} {last}"

    def get_language(self):
        return self.info.language.lower() if self.info and self.info.language else "uz"
    
    def __str__(self):
        return f"{self.phone} {self.role}"

    def prepare_odoo_data(self):
        # Try to use cached UserInfo first (set by UserInfo.save())
        # This ensures we get the latest data when UserInfo triggers a sync
        user_info = getattr(self, '_cached_info', None)
        if user_info is None:
            # Fall back to database query if no cache
            user_info = UserInfo.objects.filter(user=self).first()
        return OdooSync.prepare_user_data(self, user_info)


# User Info Model
class UserInfo(models.Model):
    """
    This model has a OneToOne connection to the User Model and stores detailed information about the data in the User Model.
    """

    class Gender(models.TextChoices):
        MALE = "MALE", _("Male")
        FEMALE = "FEMALE", _("Female")

    class Language(models.TextChoices):
        UZ = "UZ", _("Uzbek")
        EN = "EN", _("English")
        RU = "RU", _("Russian")

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="info")
    first_name = models.CharField(max_length=255, null=True, blank=True)
    last_name = models.CharField(max_length=255, null=True, blank=True)
    address = models.CharField(max_length=255, null=True, blank=True)
    avatar = models.ImageField(upload_to=avatar_upload_to, blank=True, null=True)

    language = models.CharField(choices=Language.choices, default=Language.UZ, max_length=20)

    birth_date = models.DateField(null=True, blank=True)
    gender = models.CharField(
        max_length=10, choices=Gender.choices, null=True, blank=True
    )
    referral_code = models.CharField(max_length=32, unique=True, null=True, blank=True)
    referral_link = models.CharField(max_length=255, null=True, blank=True)
    referral_count = models.IntegerField(default=0)
    is_referred = models.BooleanField(default=False)

    def generate_referral_code(self):
        return uuid.uuid4().hex[:16].upper()

    def save(self, *args, **kwargs):
        # Automatically set is_referred based on Referral table
        self.is_referred = Referral.objects.filter(referred=self.user).exists()

        # Only generate referral code if empty
        if not self.referral_code:
            self.referral_code = self.generate_referral_code()

        if not self.referral_link:
            self.referral_link = f"https://carland.uz/login?ref={self.referral_code}"

        super().save(*args, **kwargs)

        # Force User sync to Odoo when UserInfo is created or updated
        # We need to directly trigger the Odoo sync operation
        user = self.user

        def trigger_user_sync():
            # Ensure the User save understands fresh info is available
            user._cached_info = self
            user.send_odoo = True
            user.sync_status = "updated"

            try:
                user.save()
            except Exception as exc:
                logger.exception(
                    "Failed to trigger Odoo sync via user.save() for user %s: %s",
                    user.pk,
                    exc,
                )
            finally:
                if hasattr(user, "_cached_info"):
                    delattr(user, "_cached_info")

        connection = transaction.get_connection()
        if connection.in_atomic_block:
            transaction.on_commit(trigger_user_sync)
        else:
            trigger_user_sync()

    def __str__(self):
        return f"{self.first_name} - {self.last_name} - {self.user.phone}"


class Address(SyncSoftDeleteMixin):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="address")
    name = models.CharField(max_length=255, help_text="Your address name")
    region = models.ForeignKey(
        "app.Region", on_delete=models.CASCADE, related_name="addresses"
    )
    district = models.ForeignKey(
        "app.District", on_delete=models.CASCADE, related_name="addresses"
    )
    yandex_link = models.URLField(help_text="Yandex link")
    additional = models.CharField(max_length=255, null=True, blank=True)
    building = models.CharField(max_length=255, blank=True, null=True)
    floor = models.IntegerField(blank=True, null=True)
    demophone_code = models.CharField(max_length=20, blank=True, null=True)
    is_main = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} - {self.user.phone} on {self.region} {self.district}"

    def save(self, *args, **kwargs):
        if self.is_main:
            Address.objects.filter(user=self.user).exclude(pk=self.pk).update(
                is_main=False
            )
        super().save(*args, **kwargs)

    def prepare_odoo_data(self):
        return OdooSync.prepare_address_data(self)


class OTP(models.Model):
    phone_regex = RegexValidator(
        regex=r"^(\+998|998)\d{9}$",
        message="Phone number must be in correct format: +998XXXXXXXXX or 998XXXXXXXXX",
    )
    phone = models.CharField(validators=[phone_regex], max_length=20, unique=True)
    code = models.CharField(max_length=6)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now=True)
    expired_at = models.DateTimeField()

    def __str__(self):
        return f"OTP for {self.phone}"


class MessageLog(models.Model):
    class MessageStatus(models.TextChoices):
        SENT = "SENT", _("Sent")
        FAILED = "FAILED", _("Failed")
        PENDING = "PENDING", _("Pending")

    send_by = models.CharField(max_length=255)
    recipient = models.CharField(max_length=255)
    sent_at = models.DateTimeField(auto_now_add=True)
    content = models.TextField()
    status = models.CharField(
        max_length=10, choices=MessageStatus.choices, default=MessageStatus.PENDING
    )
    error_details = models.TextField(null=True, blank=True)

    content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, null=True, blank=True
        )
    
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey("content_type", "object_id")

    message_type = models.CharField(
        max_length=50, null=True, blank=True,
        help_text="Type of the message, e.g., 'SMS', 'Email', etc."
    )
    context = models.JSONField(
        null=True, blank=True,
        help_text="Additional context for the message, e.g., {'order_id': 123}"
    )

    def __str__(self):
        return (
            f"Message to {self.recipient} on {self.sent_at} with status {self.status}"
        )


class MulticardConfig(models.Model):
    application_id = models.CharField(max_length=255, default="Multicard Id")
    secret_key = models.CharField(max_length=255, default="Secret Id")
    store_id = models.CharField(max_length=100, default="950")

    class Meta:
        verbose_name = _("Multicard Configuration")
        verbose_name_plural = _("Multicard Configurations")

    def save(self, *args, **kwargs):
        if not MulticardConfig.objects.exists():
            super().save(*args, **kwargs)
        else:
            raise Exception("Only one MulticardConfig instance allowed")

    @classmethod
    def get_instance(cls):
        return cls.objects.first()


class Referral(models.Model):
    referrer = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="referrals_made"
    )
    referred = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="referred_by"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("referrer", "referred")

    def __str__(self):
        return f"{self.referrer.phone} referred {self.referred.phone}"



class UserShareInfo(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="shared_info")
    unique_code = models.ForeignKey(QRCode, on_delete=models.CASCADE, related_name="shared_info")
    phone_number_allowed = models.BooleanField(default=False)


    def __str__(self):
        return f"Share info for {self.user.phone} - Code: {self.unique_code} - Allowed: {self.phone_number_allowed}"
    
class NotificationMessages(models.Model):
    message_uz = models.CharField(max_length=255)
    message_ru = models.CharField(max_length=255,null=True, blank=True)
    message_en = models.CharField(max_length=255,null=True, blank=True)