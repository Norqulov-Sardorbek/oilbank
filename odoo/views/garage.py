from rest_framework import viewsets
from app.models.garage import (
    Firm,
    CarModel,
    SomeColor,
    CarColor,
    Car,
    OilChangedHistory,
)
from odoo.custom_filter import OdooIDFilterSet
from odoo.serializers.garage import (
    FirmSerializer,
    CarModelSerializer,
    SomeColorSerializer,
    CarColorSerializer,
    CarSerializer,
    OilChangedHistorySerializer,
)
from rest_framework.permissions import AllowAny
from .custom_base_viewset import OdooBaseViewSet


class FirmViewSet(OdooBaseViewSet):
    permission_classes = [AllowAny]
    queryset = Firm.objects.all()
    serializer_class = FirmSerializer
    filterset_class = OdooIDFilterSet
    lookup_field = "odoo_id"


class CarModelViewSet(OdooBaseViewSet):
    permission_classes = [AllowAny]
    queryset = CarModel.objects.all()
    serializer_class = CarModelSerializer
    filterset_class = OdooIDFilterSet
    lookup_field = "odoo_id"


class SomeColorViewSet(OdooBaseViewSet):
    permission_classes = [AllowAny]
    queryset = SomeColor.objects.all()
    serializer_class = SomeColorSerializer
    filterset_class = OdooIDFilterSet
    lookup_field = "odoo_id"


class CarColorViewSet(OdooBaseViewSet):
    permission_classes = [AllowAny]
    queryset = CarColor.objects.all()
    serializer_class = CarColorSerializer
    filterset_class = OdooIDFilterSet
    lookup_field = "odoo_id"


class CarViewSet(OdooBaseViewSet):
    permission_classes = [AllowAny]
    queryset = Car.objects.all()
    serializer_class = CarSerializer
    filterset_class = OdooIDFilterSet
    lookup_field = "odoo_id"


class OilChangedHistoryViewSet(OdooBaseViewSet):
    permission_classes = [AllowAny]
    queryset = OilChangedHistory.objects.all()
    serializer_class = OilChangedHistorySerializer
    filterset_class = OdooIDFilterSet
    lookup_field = "odoo_id"

    def create(self, request, *args, **kwargs):
        print("\n\n\n\n\n\n\nIncoming POST data:", request.data)
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        print("\n\n\n\n\n\n\nIncoming POST data:", request.data)
        return super().update(request, *args, **kwargs)
