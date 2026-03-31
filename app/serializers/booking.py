import random
from rest_framework import serializers
from app.models.booking import BookingRating, Booking, Resource
from app.models.company_info import Branch
from datetime import timedelta
from django.utils.translation import gettext_lazy as _
from app.serializers.company_info import BranchListSerializer
from app.serializers.garage import CarShortSerializer


class BookingRatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = BookingRating
        fields = [
            "id",
            "odoo_id",
            "reviewer",
            "booking",
            "rating",
            "description",
            "rating_type",
        ]
        read_only_fields = ["reviewer"]

    def create(self, validated_data):
        # Automatically set the 'reviewer' to the currently authenticated user
        user = self.context["request"].user
        validated_data["reviewer"] = user
        return super().create(validated_data)


class DailySlotsSerializer(serializers.Serializer):
    date = serializers.DateField()
    day_name = serializers.CharField()
    is_past = serializers.BooleanField()
    slots = serializers.ListField(child=serializers.DictField())


class BookingCreateSerializer(serializers.ModelSerializer):
    branch_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Booking
        fields = ["id", "branch_id", "car", "start_time", "source"]
        read_only_fields = ["id", "status", "end_time", "appointment"]

    def validate(self, data):
        user = self.context["request"].user
        branch_id = data.pop("branch_id")
        start_time = data["start_time"]
        car = data.get("car")

        # Get appointment
        try:
            branch = Branch.objects.get(id=branch_id)
            appointment = branch.appointment.order_by("-id").first()
        except (Branch.DoesNotExist, AttributeError):
            raise serializers.ValidationError(_("Branch or appointment not found."))

        end_time = start_time + timedelta(minutes=appointment.duration)

        # UniqueConstraint: User cannot double-book
        if Booking.objects.filter(
            appointment=appointment,
            start_time=start_time,
            user=user,
            status__in=["CONFIRMED", "PENDING"],
        ).exists():
            raise serializers.ValidationError(
                _("You already have a booking for this slot.")
            )

        # UniqueConstraint: Car cannot double-book
        if (
            car
            and Booking.objects.filter(
                appointment=appointment,
                start_time=start_time,
                car=car,
                status__in=["CONFIRMED", "PENDING"],
            ).exists()
        ):
            raise serializers.ValidationError(
                _("This car is already booked for this slot.")
            )

        # Find an available resource
        available_resources = self.get_available_resources(
            appointment, start_time, end_time
        )
        if not available_resources:
            raise serializers.ValidationError(
                _("No available resources for this time slot.")
            )

        # Randomly select an available resource
        selected_resource = random.choice(available_resources)

        # Update fields
        data.update(
            {
                "appointment": appointment,
                "end_time": end_time,
                "resource": selected_resource,
            }
        )

        return data

    def get_available_resources(self, appointment, start_time, end_time):
        """Return a list of Resources not booked during the given time slot."""
        all_resources = appointment.resources.all()
        booked_resources = Resource.objects.filter(
            bookings__appointment=appointment,
            bookings__start_time__lt=end_time,
            bookings__end_time__gt=start_time,
            bookings__status__in=["CONFIRMED", "PENDING"],
        ).distinct()
        return [r for r in all_resources if r not in booked_resources]

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)

class BookingGetSerializer(serializers.ModelSerializer):
    branch = BranchListSerializer()
    car = CarShortSerializer()
    has_rated = serializers.SerializerMethodField(read_only=True)
    given_rating = serializers.SerializerMethodField(read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Booking
        fields = [
            "id",
            "branch",
            "start_time",
            "status",
            "car",
            "created_at",
            "confirmed_at",
            "cancelled_at",
            "completed_at",
            "has_rated",
            "given_rating",
            "status_display",
        ]

    def get_has_rated(self, obj):
        return BookingRating.objects.filter(booking=obj).exists()

    def get_given_rating(self, obj):
        rating = BookingRating.objects.filter(booking=obj).first()
        return (
            BookingRatingSerializer(
                rating, context={"request": self.context.get("request")}
            ).data
            if rating
            else None
        )
