from django.contrib.auth import get_user_model
from django.db import models
from uuid import uuid4
import os
from .log_connection import SyncSoftDeleteMixin
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


User = get_user_model()


def notification_upload_to(instance, filename):
    exc = f"{filename}".split(".")[-1]
    filename = f"{uuid4()}.{exc}"
    return os.path.join("notification", filename)


class NotificationTemplate(SyncSoftDeleteMixin):
    odoo_id = models.CharField(max_length=255, null=True, blank=True)
    title = models.CharField(max_length=255)
    creator = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="notification_templates",
    )
    send_users = models.ManyToManyField(
        User, related_name="notification_templates_sent"
    )
    read_users = models.ManyToManyField(
        User, related_name="notification_templates_read"
    )
    description = models.TextField()
    condition = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class Notification(SyncSoftDeleteMixin):
    odoo_id = models.CharField(max_length=255, null=True, blank=True)
    title_uz = models.CharField(max_length=255, null=True, blank=True)
    title_ru = models.CharField(max_length=255, null=True, blank=True)
    title_en = models.CharField(max_length=255, null=True, blank=True)
    message_uz = models.TextField(null=True, blank=True)
    message_ru = models.TextField(null=True, blank=True)
    message_en = models.TextField(null=True, blank=True)
    creator = models.ForeignKey(
        User, on_delete=models.SET_NULL, blank=True, null=True, related_name="notifications"
    )
    send_users = models.ManyToManyField(
        User, related_name="notifications_sent", blank=True
    )
    image = models.ImageField(upload_to=notification_upload_to, blank=True)
    read_users = models.ManyToManyField(
        User, related_name="notifications_read", blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')

    notification_type = models.CharField(
        max_length=50,
        default='general',
        help_text="Type of notification (e.g., oil_change_reminder, booking_confirmation)"
    )
    context = models.JSONField(
        null=True,
        blank=True,
        help_text="Additional context like days_until_expiration or booking details"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['content_type', 'object_id', 'notification_type', 'context'],
                name='unique_notification'
            )
        ]

    @property
    def read_count(self):
        return self.read_users.count()

    def mark_as_read(self, user):
        if user not in self.read_users.all():
            self.read_users.add(user)
            self.save()

    def __str__(self):
        return self.title_uz or self.title_ru or self.title_en or "No title"
