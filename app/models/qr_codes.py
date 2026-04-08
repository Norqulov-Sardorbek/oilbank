from uuid import uuid4
from django.db import models
from django.utils.translation import gettext_lazy as _


class QRCode(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    unique_code = models.CharField(max_length=255, unique=True)
    image = models.ImageField(upload_to='qr_codes/')
    
    def __str__(self):
        return self.unique_code