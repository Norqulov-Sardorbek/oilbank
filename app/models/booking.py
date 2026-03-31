from django.db import models
from django.contrib.auth import get_user_model
from datetime import timedelta, timezone
from django.core.exceptions import ValidationError
from django.utils import timezone
import random, string
from django.utils.translation import gettext_lazy as _
from .log_connection import SyncSoftDeleteMixin

User = get_user_model()
from ..utils.odoo_sync_utils import OdooSync


def generate_unique_booking_name():
    chars = string.ascii_uppercase.replace("I", "").replace(
        "O", ""
    ) + string.digits.replace("0", "").replace("1", "")
    max_attempts = 50
    # for _ in range(max_attempts):
    name = "".join(random.choices(chars, k=6))
    # if not Booking.objects.filter(name=name).exists():
    return name
    # raise ValidationError("Unable to generate a unique name after multiple attempts.")


class Booking(SyncSoftDeleteMixin):
    STATUS_CHOICES = [
        ("PENDING", _("Pending")),
        ("CONFIRMED", _("Confirmed")),
        ("CANCELLED", _("Cancelled")),
        ("COMPLETED", _("Completed")),
        ("NO_SHOW", _("No Show")),
    ]

    SOURCE_CHOICES = [
        ("WEB", _("Web")),
        ("MOBILE", _("Mobile")),
        ("TG_MINI_APP", _("Telegram Mini App")),
    ]

    odoo_id = models.CharField(max_length=255, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="bookings")
    appointment = models.ForeignKey(
        "Appointment",
        on_delete=models.CASCADE,
        related_name="bookings",
        null=True,
        blank=True,
    )
    branch = models.ForeignKey(
        "Branch",
        on_delete=models.CASCADE,
        related_name="bookings",
        null=True,
        blank=True,
    )
    car = models.ForeignKey(
        "Car", on_delete=models.CASCADE, related_name="bookings", null=True, blank=True
    )
    resource = models.ForeignKey(
        "Resource",
        on_delete=models.CASCADE,
        related_name="bookings",
        null=True,
        blank=True,
    )

    name = models.CharField(
        max_length=6, unique=True, default=generate_unique_booking_name
    )
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default="WEB")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")

    notes = models.TextField(blank=True)
    cancellation_reason = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["start_time"]
        indexes = [
            models.Index(fields=["start_time"]),
            models.Index(fields=["status"]),
            models.Index(fields=["branch", "start_time"]),
            models.Index(fields=["user", "start_time"]),
            models.Index(fields=["appointment", "start_time"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["appointment", "start_time", "user"],
                name="unique_user_booking_without_car_per_slot",
                condition=(
                    models.Q(status__in=["CONFIRMED", "PENDING"])
                    & models.Q(car__isnull=True)
                ),
            ),
            models.UniqueConstraint(
                fields=["appointment", "start_time", "car"],
                name="unique_car_booking_per_slot",
                condition=(
                    models.Q(status__in=["CONFIRMED", "PENDING"])
                    & models.Q(car__isnull=False)
                ),
            ),
            models.UniqueConstraint(
                fields=["appointment", "start_time", "resource"],
                name="unique_resource_booking_per_slot",
                condition=(
                    models.Q(status__in=["CONFIRMED", "PENDING"])
                    & models.Q(resource__isnull=False)
                ),
            ),
        ]

    def save(self, *args, **kwargs):
        if not self.end_time and self.appointment and self.start_time:
            self.end_time = self.start_time + timedelta(
                minutes=self.appointment.duration
            )
        if not self.branch and self.appointment:
            self.branch = self.appointment.branch
        if self.status == "CONFIRMED" and not self.confirmed_at:
            self.confirmed_at = timezone.now()
        elif self.status == "CANCELLED" and not self.cancelled_at:
            self.cancelled_at = timezone.now()
        elif self.status == "COMPLETED" and not self.completed_at:
            self.completed_at = timezone.now()
        if (
            self.status in ["CONFIRMED", "PENDING"]
            and self.resource
            and self.appointment
            and not self.is_available()
        ):
            raise ValidationError("No available resources for this slot.")
        super().save(*args, **kwargs)

    def __str__(self):
        car_info = f" - {self.car.number}" if self.car else ""
        resource_info = f" - {self.resource.name}" if self.resource else ""
        return f"Booking #{self.id}{car_info}{resource_info} for {self.appointment.name if self.appointment else ''} at {self.start_time.strftime('%Y-%m-%d %H:%M')}"

    @property
    def duration(self):
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds() / 60
        return self.appointment.duration if self.appointment else 0

    def is_available(self):
        if (
            not self.appointment
            or not self.start_time
            or not self.end_time
            or not self.resource
        ):
            return False
        return not Booking.objects.filter(
            appointment=self.appointment,
            resource=self.resource,
            start_time__lt=self.end_time,
            end_time__gt=self.start_time,
            status__in=["CONFIRMED", "PENDING"],
        ).exclude(id=self.id).exists()

    def prepare_odoo_data(self):
        return OdooSync.prepare_booking_data(self)


class Resource(SyncSoftDeleteMixin):
    odoo_id = models.CharField(max_length=255, null=True, blank=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.name}"


class Appointment(SyncSoftDeleteMixin):
    DAY_CHOICES = [
        (0, _("Monday")),
        (1, _("Tuesday")),
        (2, _("Wednesday")),
        (3, _("Thursday")),
        (4, _("Friday")),
        (5, _("Saturday")),
        (6, _("Sunday")),
    ]

    odoo_id = models.CharField(max_length=255, null=True, blank=True)
    branch = models.ForeignKey(  # One-to-one ensures one appointment per branch
        "Branch",
        on_delete=models.CASCADE,
        related_name="appointment",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=100)  # e.g., "Oil Change", "Tire Rotation"
    duration = models.PositiveIntegerField(default=30, help_text="Duration in minutes")
    resources = models.ManyToManyField(
        Resource, related_name="appointments", blank=True
    )

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.name} ({self.duration} mins)"


class AppointmentWorkingDay(SyncSoftDeleteMixin):
    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.CASCADE,
        related_name="working_days",
        null=True,
        blank=True,
    )
    odoo_id = models.CharField(max_length=255, null=True, blank=True)
    day = models.PositiveSmallIntegerField(choices=Appointment.DAY_CHOICES)
    opening_time = models.TimeField(default="09:00")
    closing_time = models.TimeField(default="17:00")

    class Meta:
        ordering = ["id"]

    def __str__(self):
        appointment_str = (
            str(self.appointment) if self.appointment else "No Appointment"
        )
        day_str = self.get_day_display() if self.get_day_display() else "Unknown Day"
        return f"{appointment_str} - {day_str} {self.opening_time}-{self.closing_time}"


class BookingRating(SyncSoftDeleteMixin):
    class BookingRatingTypes(models.TextChoices):
        GOOD = "GOOD", _("Good")
        AVERAGE = "AVERAGE", _("Average")
        BAD = "BAD", _("Bad")

    odoo_id = models.CharField(max_length=255, null=True, blank=True)
    reviewer = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="given_reviews"
    )
    booking = models.ForeignKey(
        Booking, on_delete=models.CASCADE, related_name="given_reviews"
    )
    rating = models.DecimalField(max_digits=2, decimal_places=1)
    rating_type = models.CharField(
        max_length=10,
        choices=BookingRatingTypes.choices,
        default=BookingRatingTypes.AVERAGE,
    )
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Rating #{self.id} by {self.reviewer} for Booking #{self.booking.id}"
