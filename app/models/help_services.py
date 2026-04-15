from django.db import models


class HelpService(models.Model):
    name_uz = models.CharField(max_length=255)
    name_ru = models.CharField(max_length=255)
    name_en = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    description_ru = models.TextField(blank=True, null=True)
    description_en = models.TextField(blank=True, null=True)
    icon = models.ImageField(upload_to="help_services/icons/", blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "Yordam xizmati"
        verbose_name_plural = "Yordam xizmatlari"

    def __str__(self):
        return self.name_uz

class HelpServiceEmployee(models.Model):
    service = models.ForeignKey(
        HelpService,
        on_delete=models.CASCADE,
        related_name="employees",
    )
    name = models.CharField(max_length=255)
    icon = models.ImageField(upload_to="help_services/employees/", blank=True, null=True)
    phone = models.CharField(max_length=30)

    class Meta:
        verbose_name = "Yordam xizmati xodimi"
        verbose_name_plural = "Yordam xizmati xodimlari"

    def __str__(self):
        return f"{self.name} ({self.service.name_uz})"

