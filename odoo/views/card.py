from rest_framework.response import Response
from rest_framework import status
from app.models.card import Balance, BalanceStatus, Cashback
from ..custom_filter import OdooIDFilterSet
from ..serializers.card import (
    BalanceSerializer,
    CashbackSerializer,
    BalanceStatusSerializer,
)
from rest_framework.permissions import AllowAny
from rest_framework import status
from user.models import User
from .custom_base_viewset import OdooBaseViewSet


class BalanceViewSet(OdooBaseViewSet):
    permission_classes = [AllowAny]
    queryset = Balance.objects.all()
    serializer_class = BalanceSerializer
    filter_class = OdooIDFilterSet
    lookup_field = "odoo_id"


class BalanceStatusViewSet(OdooBaseViewSet):
    permission_classes = [AllowAny]
    queryset = BalanceStatus.objects.all()
    serializer_class = BalanceStatusSerializer
    filter_class = OdooIDFilterSet
    lookup_field = "odoo_id"

    def create(self, request, *args, **kwargs):
        print(
            f"\n\n\n\n\n\n\nIncoming Balance Status POST data (create): {request.data}"
        )
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        print(
            f"\n\n\n\n\n\n\nIncoming Balance Status POST data (update): {request.data}"
        )
        return super().update(request, *args, **kwargs)


class CashbackViewSet(OdooBaseViewSet):
    permission_classes = [AllowAny]
    queryset = Cashback.objects.all()
    serializer_class = CashbackSerializer
    filter_class = OdooIDFilterSet
    lookup_field = "odoo_id"
