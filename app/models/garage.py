from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from .log_connection import SyncSoftDeleteMixin
from ..utils.utils import OdooSync
from .product import OilBrand, FilterBrand
from .order import Order, RatingType
from app.utils.validators import is_valid_uz_car_number

User = get_user_model()


class Firm(SyncSoftDeleteMixin):
    """
    Model for car manufacturers
    """

    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def prepare_odoo_data(self):
        return OdooSync.prepare_firm_data(self)


class CarModel(SyncSoftDeleteMixin):
    """
    Model for car models
    """

    name = models.CharField(max_length=255)
    firm = models.ForeignKey(
        Firm, on_delete=models.SET_NULL, null=True, blank=True, related_name="car_model"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.firm if self.firm else 'Unknown'} {self.name}"

    def prepare_odoo_data(self):
        return OdooSync.prepare_car_model_data(self)


class SomeColor(SyncSoftDeleteMixin):
    name_en = models.CharField(max_length=255)
    name_uz = models.CharField(max_length=255)
    name_ru = models.CharField(max_length=255)
    color_code = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name_en

    def prepare_odoo_data(self):
        return OdooSync.prepare_some_color_data(self)


class CarColor(SyncSoftDeleteMixin):
    some_color = models.ForeignKey(
        SomeColor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="car_colors",
    )
    car_model = models.ForeignKey(
        CarModel, on_delete=models.CASCADE, related_name="car_colors"
    )
    image = models.ImageField(upload_to="car_colors/", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.some_color if self.some_color else 'Unknown'} {self.car_model if self.car_model else 'Unknown'}"

    def prepare_odoo_data(self):
        return OdooSync.prepare_car_color_data(self)


class CarManager(models.Manager):
    def create_with_default_color(self, **kwargs):
        """Create a car with default white color if no color is provided"""
        car = self.model(**kwargs)
        
        if not car.color and car.model:
            car.color = car.get_default_white_color()
        
        car.save()
        return car

class Car(SyncSoftDeleteMixin):
    objects = CarManager()
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="cars")
    number = models.CharField(
        max_length=20, help_text="License plate or car number (Uzbekistan)"
    )
    firm = models.ForeignKey(
        Firm, on_delete=models.SET_NULL, blank=True, null=True, related_name="cars"
    )
    model = models.ForeignKey(
        CarModel, on_delete=models.SET_NULL, blank=True, null=True, related_name="cars"
    )
    color = models.ForeignKey(
        CarColor, on_delete=models.SET_NULL, blank=True, null=True, related_name="cars"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        brand_name = self.firm.name if self.firm else "Unknown Brand"
        model_name = self.model.name if self.model else "Unknown Model"  # Fixed this line
        color_name = (
            self.color.some_color.name_en
            if self.color and self.color.some_color
            else "Unknown Color"
        )
        return f"{self.number} - {brand_name} {model_name} ({color_name})"

    def save(self, *args, **kwargs):
        # Set default white color if no color is provided and this is a new instance
        if not self.pk and not self.color:
            self.color = self.get_default_white_color()
        super().save(*args, **kwargs)

    def get_default_white_color(self):
        """
        Get the default white color for the car's model.
        Returns None if no white color is found.
        """
        if not self.model:
            return None
            
        try:
            # Try to find a white color for this specific car model
            # Option 1: Exact match (case-insensitive)
            white_color = SomeColor.objects.filter(
                name_en__iexact='white'
            ).first()
            
            # Option 2: If exact doesn't work, try contains (more flexible)
            if not white_color:
                white_color = SomeColor.objects.filter(
                    name_en__icontains='white'
                ).first()
            
            if white_color:
                # Get or create CarColor for this model and white color
                car_color, created = CarColor.objects.get_or_create(
                    some_color=white_color,
                    car_model=self.model,
                    defaults={'image': None}  # Will be blank if no image exists
                )
                return car_color
        except Exception:
            pass
        
        return None

    def prepare_odoo_data(self):
        return OdooSync.prepare_car_data(self)

    def clean(self):
        super().clean()
        if not is_valid_uz_car_number(self.number):
            raise ValidationError(_("Car number is not valid in Uzbekistan"))


class OilChangedHistory(SyncSoftDeleteMixin):
    class SourceChoices(models.TextChoices):
        OTHER = "other", _("Other")
        REGULAR = "regular", _("Regular")

    odoo_id = models.CharField(max_length=255, null=True, blank=True)
    car = models.ForeignKey(
        Car, on_delete=models.CASCADE, related_name="oil_change_history"
    )
    last_oil_change = models.DateTimeField()
    order = models.ForeignKey(
        Order,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="oil_change_history",
    )
    branch = models.ForeignKey(
        "app.Branch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="oil_change_history",
    )
    distance = models.PositiveIntegerField(
        help_text="Current mileage at oil change time (in km)"
    )
    duration_days = models.PositiveIntegerField(
        help_text="Duration of oil change (in days)", null=True, blank=True
    )
    oil_brand = models.ForeignKey(
        OilBrand,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="oil_change_history",
    )  # Oil brand(max_length=100)
    recommended_distance = models.PositiveIntegerField(
        help_text="Recommended distance between oil changes (in km)"
    )
    daily_distance = models.PositiveIntegerField(
        help_text="Estimated average daily distance (in km)"
    )
    filter_changed = models.BooleanField(default=False)
    filter_brand = models.ForeignKey(
        FilterBrand,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="oil_change_history",
    )

    source = models.CharField(choices=SourceChoices.choices, max_length=50)
    note = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Oil change for {self.car.number} on {self.last_oil_change}"

    def prepare_odoo_data(self):
        return OdooSync.prepare_oil_changed_history_data(self)


class OilChangeRating(SyncSoftDeleteMixin):
    odoo_id = models.CharField(max_length=255, null=True, blank=True)
    reviewer = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="oil_change_reviews"
    )
    oil_change_id = models.ForeignKey(
        OilChangedHistory, on_delete=models.CASCADE, related_name="ratings"
    )
    rating = models.IntegerField()
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    options_ids = models.ManyToManyField(RatingType, related_name="oil_change_options")

    # Ratging type change it to model
    def __str__(self):
        return f"Rating {self.rating} by {self.reviewer}"

    def prepare_odoo_data(self):
        return OdooSync.perpare_oil_change_rating(self)
