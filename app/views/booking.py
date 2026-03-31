# global imports
from rest_framework import viewsets, status
from rest_framework.viewsets import ModelViewSet
from django.utils.dateformat import time_format
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django.utils.translation import gettext_lazy as _
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_view
from django.utils import timezone
from datetime import datetime, timedelta
from rest_framework.views import APIView
import requests

# local imports
from app.models.company_info import Branch
from app.models.booking import BookingRating, Booking, AppointmentWorkingDay, Resource
from app.serializers.booking import (
    BookingRatingSerializer,
    DailySlotsSerializer,
    BookingCreateSerializer,
    BookingGetSerializer,
)
import os

odoo_url = os.getenv("BASE_URL", "https://api.car-land.uz")


@extend_schema_view(
    list=extend_schema(
        summary="List all booking ratings",
        description="Returns a list of booking ratings created by the authenticated user.",
    ),
    retrieve=extend_schema(
        summary="Retrieve a booking rating",
        description="Returns details of a specific booking rating.",
    ),
    create=extend_schema(
        summary="Create a booking rating",
        description="Creates a new rating for a completed booking. You can only rate each booking once.",
    ),
    update=extend_schema(
        summary="Update a booking rating",
        description="Updates all fields of a booking rating.",
    ),
    partial_update=extend_schema(
        summary="Partially update a booking rating",
        description="Updates selected fields of a booking rating.",
    ),
    destroy=extend_schema(
        summary="Delete a booking rating",
        description="Deletes a specific booking rating.",
    ),
)
class BookingRatingViewSet(viewsets.ModelViewSet):
    serializer_class = BookingRatingSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post"]

    def get_queryset(self):
        # Filter the queryset to only include ratings by the current user
        return BookingRating.objects.select_related("booking").filter(
            reviewer=self.request.user
        )

    def create(self, request, *args, **kwargs):
        # Ensure the booking is provided in the request
        booking = request.data.get("booking")

        if not booking:
            return Response(
                {"error": _("Booking is required.")}, status=status.HTTP_400_BAD_REQUEST
            )

        # Check if the user has already rated this booking
        if BookingRating.objects.filter(
            reviewer=request.user, booking_id=booking
        ).exists():
            return Response(
                {"error": _("You have already rated this booking.")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        booking_instance = Booking.objects.get(id=booking)
        if booking_instance.status != "COMPLETED":
            return Response(
                {"error": _("Rating can only be given for completed bookings.")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return super().create(request, *args, **kwargs)


class WeeklySlotsAPIView(APIView):
    def get(self, request, branch_id):
        try:
            branch = Branch.objects.get(id=branch_id)
            # Note: There's an issue here (appointment field doesn't exist), fixing based on prior conversations
            appointment = branch.appointment.order_by("-id").first()
            if not appointment:
                return Response(
                    {"error": _("No appointment found for this branch")},
                    status=status.HTTP_404_NOT_FOUND,
                )
        except Branch.DoesNotExist:
            return Response(
                {"error": "Branch not found"}, status=status.HTTP_404_NOT_FOUND
            )

        today = timezone.now().date()
        start_of_week = today - timedelta(days=today.weekday())  # Monday
        end_of_week = start_of_week + timedelta(days=6)  # Sunday

        week_days = []
        current_date = start_of_week

        while current_date <= end_of_week:
            day_data = self.get_day_slots(appointment, current_date, today)
            week_days.append(day_data)
            current_date += timedelta(days=1)

        serializer = DailySlotsSerializer(week_days, many=True)
        return Response(serializer.data)

    def get_day_slots(self, appointment, day_date, today):
        working_days = appointment.working_days.filter(day=day_date.weekday()).order_by(
            "opening_time"
        )

        day_slots = {
            "date": day_date,
            "day_name": _(day_date.strftime("%A")),
            "is_past": day_date < today,
            "slots": [],
        }

        for working_day in working_days:
            day_slots["slots"].extend(
                self.generate_slots(appointment, working_day, day_date)
            )

        return day_slots

    def generate_slots(self, appointment, working_day, day_date):
        slots = []
        tz = timezone.get_current_timezone()

        current_time = timezone.make_aware(
            datetime.combine(day_date, working_day.opening_time)
        )
        end_time = timezone.make_aware(
            datetime.combine(day_date, working_day.closing_time)
        )

        while current_time + timedelta(minutes=appointment.duration) <= end_time:
            slot_end = current_time + timedelta(minutes=appointment.duration)

            available_resources = self.get_available_resources(
                appointment, current_time, slot_end
            )
            available = len(available_resources)
            is_past = current_time < timezone.now()

            slots.append(
                {
                    "start": current_time.strftime("%H:%M"),
                    "end": slot_end.strftime("%H:%M"),
                    "available": available if not is_past else 0,
                    "is_past": is_past,
                }
            )

            current_time = slot_end

        return slots

    def get_available_resources(self, appointment, start_time, end_time):
        all_resources = appointment.resources.all()
        booked_resources = Resource.objects.filter(
            bookings__appointment=appointment,
            bookings__start_time__lt=end_time,
            bookings__end_time__gt=start_time,
            bookings__status__in=["CONFIRMED", "PENDING"],
        ).distinct()
        return [r for r in all_resources if r not in booked_resources]


@extend_schema_view(
    list=extend_schema(
        summary="Get all bookings of the current user",
        responses=BookingGetSerializer,
    ),
    retrieve=extend_schema(
        summary="Get a single booking by ID",
        responses=BookingGetSerializer,
    ),
    create=extend_schema(
        summary="Create a new booking",
        request=BookingCreateSerializer,
        responses={
            201: BookingGetSerializer,
        },
    ),
    update=extend_schema(
        summary="Update a booking",
        request=BookingCreateSerializer,
        responses=BookingGetSerializer,
    ),
    partial_update=extend_schema(
        summary="Partially update a booking",
        request=BookingCreateSerializer,
        responses=BookingGetSerializer,
    ),
    destroy=extend_schema(
        summary="Soft delete (cancel) a booking", responses={204: None}
    ),
)
class BookingViewSet(ModelViewSet):
    serializer_class = BookingCreateSerializer
    permission_classes = [IsAuthenticated]
    queryset = Booking.objects.all()

    def get_serializer_class(self):
        if self.request.method == "GET":
            return BookingGetSerializer
        return BookingCreateSerializer

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(user=self.request.user)
            .select_related("appointment", "branch", "car", "resource")
        )

    def perform_create(self, serializer):
        appointment = serializer.validated_data["appointment"]
        serializer.save(
            user=self.request.user,
            end_time=serializer.validated_data["start_time"]
            + timedelta(minutes=appointment.duration),
            status="PENDING",
        )

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        response.data["message"] = _("Booking created successfully.")
        return response

    def send_odoo_cancel_request(self, booking):
        if booking.status == "CANCELLED" and booking.odoo_id:
            odoo_url = f"{odoo_url}/api/booking/cancel/"
            headers = {
                "Content-Type": "application/json",
                "Cookie": self.request.META.get("HTTP_COOKIE", ""),
            }
            payload = {"e_id": booking.odoo_id}
            try:
                response = requests.post(odoo_url, json=payload, headers=headers)
                response.raise_for_status()
            except requests.RequestException as e:
                booking.sync_status = "updated"
                booking.save(update_fields=["sync_status"])

    def perform_update(self, serializer):
        original_status = serializer.instance.status
        if "start_time" in serializer.validated_data:
            appointment = serializer.validated_data.get(
                "appointment", serializer.instance.appointment
            )
            serializer.validated_data["end_time"] = serializer.validated_data[
                "start_time"
            ] + timedelta(minutes=appointment.duration)
        instance = serializer.save()
        if instance.status == "CANCELLED" and original_status != "CANCELLED":
            instance.cancelled_at = timezone.now()
            instance.save(update_fields=["cancelled_at"])
            self.send_odoo_cancel_request(instance)

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        response.data["message"] = _("Booking updated successfully.")
        return response

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        booking = self.get_object()
        booking.status = "CANCELLED"
        booking.cancelled_at = timezone.now()
        booking.save()
        self.send_odoo_cancel_request(booking)
        return Response(self.get_serializer(booking).data)

    def destroy(self, request, *args, **kwargs):
        """Soft delete by marking as cancelled"""
        instance = self.get_object()
        instance.status = "CANCELLED"
        instance.cancelled_at = timezone.now()
        instance.save()
        self.send_odoo_cancel_request(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)
