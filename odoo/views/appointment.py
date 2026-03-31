from rest_framework.viewsets import ModelViewSet
from app.models.booking import Appointment, AppointmentWorkingDay, Resource
from odoo.serializers.appointment import (
    AppointmentSerializer,
    AppointmentWorkingDaySerializer,
    ResourceSerializer,
)
from ..custom_filter import OdooIDFilterSet
from rest_framework.permissions import AllowAny
from .custom_base_viewset import OdooBaseViewSet
from rest_framework.response import Response
from rest_framework import status

class AppointmentViewSet(OdooBaseViewSet):
    permission_classes = [AllowAny]
    queryset = Appointment.objects.all()
    serializer_class = AppointmentSerializer
    filterset_class = OdooIDFilterSet
    lookup_field = "odoo_id"


class AppointmentWorkingDayViewSet(OdooBaseViewSet):
    permission_classes = [AllowAny]
    queryset = AppointmentWorkingDay.objects.all()
    serializer_class = AppointmentWorkingDaySerializer
    filterset_class = OdooIDFilterSet
    lookup_field = "odoo_id"

    def create(self, request, *args, **kwargs):
        print("Incoming Create data from AppointmentWorkingDayViewSet", request.data)
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            print("Serializer errors:", serializer.errors)  # <— add this
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        print("Incoming Update data from AppointmentWorkingDayViewSet", request.data)
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if not serializer.is_valid():
            print("Serializer errors:", serializer.errors)  # <— add this
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        self.perform_update(serializer)
        return Response(serializer.data)


class ResourceViewSet(OdooBaseViewSet):
    permission_classes = [AllowAny]
    queryset = Resource.objects.all()
    serializer_class = ResourceSerializer
    filterset_class = OdooIDFilterSet
    lookup_field = "odoo_id"
