from django.conf import settings
from ..serializers.stories_serializer import StorySerializer
from app.models import Story
from django_filters.rest_framework import DjangoFilterBackend
from ..custom_filter import OdooIDFilterSet
from rest_framework.permissions import AllowAny
from .custom_base_viewset import OdooBaseViewSet


class StoryOdooViewSet(OdooBaseViewSet):
    permission_classes = [AllowAny]
    queryset = Story.objects.all()
    serializer_class = StorySerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = OdooIDFilterSet
    lookup_field = "odoo_id"