from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model
from .log_connection import SyncSoftDeleteMixin
from uuid import uuid4
import os

User = get_user_model()


def story_upload_to(instance, filename):
    ext = str(filename).split(".")[-1]
    filename = f"{uuid4()}.{ext}"
    return os.path.join(f"stories/{instance.user.id}/{filename}")


class Story(SyncSoftDeleteMixin):
    odoo_id = models.CharField(max_length=255, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="stories")
    date = models.DateField(null=True, blank=True)
    time = models.TimeField(null=True, blank=True)
    image_en = models.ImageField(upload_to=story_upload_to, blank=True, null=True)
    image_ru = models.ImageField(upload_to=story_upload_to, blank=True, null=True)
    image_uz = models.ImageField(upload_to=story_upload_to, blank=True, null=True)
    video_en = models.FileField(upload_to=story_upload_to, blank=True, null=True)
    video_ru = models.FileField(upload_to=story_upload_to, blank=True, null=True)
    video_uz = models.FileField(upload_to=story_upload_to, blank=True, null=True)
    caption_en = models.CharField(max_length=255, blank=True, null=True)
    caption_ru = models.CharField(max_length=255, blank=True, null=True)
    caption_uz = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    read_users = models.ManyToManyField(
        User, related_name="story_read_users", blank=True
    )
    send_users = models.ManyToManyField(
        User, related_name="story_send_users", blank=True
    )

    def clean(self):
        super().clean()

    def __str__(self):
        return f"{self.user.phone} Story at {self.created_at}"

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
