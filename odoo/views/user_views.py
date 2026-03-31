from rest_framework import viewsets
from django_filters.rest_framework import DjangoFilterBackend
from user.models import User, Address
from ..serializers.user_serializer import UserSerializer, AddressSerializer
from ..custom_filter import OdooIDFilterSet
from rest_framework.permissions import AllowAny
from .custom_base_viewset import OdooBaseViewSet


class UserViewSet(OdooBaseViewSet):
    permission_classes = [AllowAny]
    queryset = User.objects.all()
    serializer_class = UserSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = OdooIDFilterSet
    lookup_field = "odoo_id"


class AddressViewSet(OdooBaseViewSet):
    permission_classes = [AllowAny]
    queryset = Address.objects.all()
    serializer_class = AddressSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = OdooIDFilterSet
    lookup_field = "odoo_id"
