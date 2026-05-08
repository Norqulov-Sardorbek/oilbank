from uuid import uuid4
from django.db import models
from django.utils.translation import gettext_lazy as _


class QRCode(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    serial_number = models.PositiveIntegerField(unique=True, null=True, blank=True)
    unique_code = models.CharField(max_length=255, unique=True)
    image = models.ImageField(upload_to='qr_codes/')

    class Meta:
        ordering = ['serial_number']

    def __str__(self):
        if self.serial_number:
            return f"QR-{self.serial_number}"
        return self.unique_code

    @property
    def display_name(self):
        return f"QR-{self.serial_number}" if self.serial_number else self.unique_code