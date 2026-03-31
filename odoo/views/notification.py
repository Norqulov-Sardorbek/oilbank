from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import viewsets
from django_filters.rest_framework import DjangoFilterBackend
from app.models.notification import Notification, NotificationTemplate
from app.serializers.notification import (
    NotificationSerializer,
    NotificationTemplateSerializer,
)
from ..custom_filter import OdooIDFilterSet
from rest_framework.permissions import AllowAny

from .custom_base_viewset import OdooBaseViewSet

@extend_schema(
    tags=["Notification Templates"],
    description="CRUD endpoints for NotificationTemplate objects. Supports filtering by `odoo_id`.\n"
    "`odoo_id=null` will return records where `odoo_id` is null or empty.",
    parameters=[
        OpenApiParameter(
            name="odoo_id",
            description="Filter by Odoo ID. Use `odoo_id=null` to get records with null or empty odoo_id.",
            required=False,
            type=str,
        )
    ],
)
class NotificationTemplateViewSet(OdooBaseViewSet):
    permission_classes = [AllowAny]
    queryset = NotificationTemplate.objects.all()
    serializer_class = NotificationTemplateSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = OdooIDFilterSet
    lookup_field = "odoo_id"


@extend_schema(
    tags=["Notifications"],
    description="CRUD endpoints for Notification objects. Supports filtering by `odoo_id`.\n"
    "`odoo_id=null` will return records where `odoo_id` is null or empty.",
    parameters=[
        OpenApiParameter(
            name="odoo_id",
            description="Filter by Odoo ID. Use `odoo_id=null` to get records with null or empty odoo_id.",
            required=False,
            type=str,
        )
    ],
)
class NotificationViewSet(OdooBaseViewSet):
    permission_classes = [AllowAny]
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = OdooIDFilterSet
    lookup_field = "odoo_id"
