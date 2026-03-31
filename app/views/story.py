# global imports
import os

from django.db.models import Q
from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
    OpenApiParameter,
    OpenApiExample,
)
from drf_spectacular.types import OpenApiTypes
from django.utils.translation import get_language
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.http import Http404, HttpResponse, FileResponse
from rest_framework.views import APIView
from django.http import FileResponse
from rest_framework.response import Response
from rest_framework import viewsets
from django.utils import timezone
from rest_framework import status

# local imports
from user.models import User
from app.models.story import Story
from app.serializers.story import (
    StorySerializer,
    StoryGetSerializer,
    StoryPostSerializer,
)
import os
import re
from wsgiref.util import FileWrapper


@extend_schema_view(
    list=extend_schema(
        summary="List stories",
        description="Returns stories based on user role. Admins and regular users see all stories, others see only active ones.",
        parameters=[
            OpenApiParameter(
                name="expired",
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description="Filter by expired status (admin/regular users only)",
                required=False,
            )
        ],
        responses={200: StoryGetSerializer(many=True), 403: OpenApiTypes.OBJECT},
    ),
    retrieve=extend_schema(
        summary="Retrieve story",
        description="Returns story details and marks it as read for the current user",
        responses={200: StoryGetSerializer, 404: OpenApiTypes.OBJECT},
        examples=[
            OpenApiExample(
                "Success Response",
                value={
                    "id": 1,
                    "title": "Example Story",
                    "content": "Story content...",
                    "is_expired": False,
                    # ... other fields
                },
                response_only=True,
                status_codes=["200"],
            ),
            OpenApiExample(
                "Expired Story",
                value={"detail": "Story has expired."},
                response_only=True,
                status_codes=["404"],
            ),
        ],
    ),
    create=extend_schema(
        summary="Create story",
        description="Creates a new story (admin/regular users only)",
        request=StoryPostSerializer,
        responses={201: StoryGetSerializer, 400: OpenApiTypes.OBJECT},
        examples=[
            OpenApiExample(
                "Request Example",
                value={
                    "title": "New Story",
                    "content": "Story content...",
                    "expires_at": "2023-12-31T23:59:59Z",
                    # ... other required fields
                },
                request_only=True,
            )
        ],
    ),
    update=extend_schema(
        summary="Update story",
        description="Full update of a story (admin/regular users only)",
        request=StoryPostSerializer,
        responses={200: StoryGetSerializer, 400: OpenApiTypes.OBJECT},
    ),
    partial_update=extend_schema(
        summary="Partial update story",
        description="Partial update of a story (admin/regular users only)",
        request=StoryPostSerializer,
        responses={200: StoryGetSerializer, 400: OpenApiTypes.OBJECT},
    ),
    destroy=extend_schema(
        summary="Delete story",
        description="Deletes a story (admin/regular users only)",
        responses={204: None, 403: OpenApiTypes.OBJECT},
    ),
)
class StoryViewSet(viewsets.ModelViewSet):
    queryset = Story.objects.all()
    serializer_class = StorySerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        now = timezone.now()
        base_qs = Story.objects.filter(expires_at__gte=now)

        if self.request.user.is_authenticated:
            return base_qs.filter(
                Q(send_users__isnull=True) | Q(send_users=self.request.user)
            ).distinct()
        else:
            return base_qs.filter(send_users__isnull=True)

    def get_serializer_class(self):
        if self.request.method == "POST":
            return StoryPostSerializer
        if self.request.method in ["PATCH", "PUT"]:
            return StoryPostSerializer
        if self.request.method == "GET":
            return StoryGetSerializer
        return StorySerializer

    @extend_schema(
        request=StoryPostSerializer,
        responses={201: StoryGetSerializer, 400: OpenApiTypes.OBJECT},
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(
                serializer.data, status=status.HTTP_201_CREATED, headers=headers
            )
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        request=StoryPostSerializer,
        responses={200: StoryGetSerializer, 400: OpenApiTypes.OBJECT},
    )
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)

        if serializer.is_valid():
            self.perform_update(serializer)
            return Response(serializer.data)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(responses={200: StoryGetSerializer, 404: OpenApiTypes.OBJECT})
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()

        if instance.is_expired:
            return Response(
                {"detail": _("Story has expired.")}, status=status.HTTP_404_NOT_FOUND
            )

        user = self.request.user

        if not instance.read_users.filter(id=user.id).exists():
            instance.read_users.add(user)

        serializer = self.get_serializer(instance)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["patch"], permission_classes=[IsAuthenticated])
    def mark_as_viewed(self, request, pk=None):
        story = self.get_object()
        if (
            story.send_users.count() == 0
            or story.send_users.filter(id=request.user.id).exists()
        ):
            story.read_users.add(request.user)
            return Response(
                {"status": _("Story marked as read")}, status=status.HTTP_200_OK
            )
        else:
            return Response(
                {"status": _("You are not authorized to mark this story as viewed")},
                status=status.HTTP_403_FORBIDDEN,
            )


class StoryVideoView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk):
        story = get_object_or_404(Story, pk=pk)
        lang = get_language()

        video_field = {
            "en": story.video_en,
            "ru": story.video_ru,
            "uz": story.video_uz,
        }.get(lang, story.video_en)

        if not video_field:
            return HttpResponse(status=404, content="Video not found.")

        file_path = video_field.path
        file_size = os.path.getsize(file_path)
        range_header = request.headers.get("Range", "")

        if not range_header:
            return FileResponse(open(file_path, "rb"), content_type="video/mp4")

        try:
            range_type, range_value = range_header.strip().split("=")
            start_str, end_str = range_value.split("-")
            start = int(start_str)
            end = int(end_str) if end_str else file_size - 1
            end = min(end, file_size - 1)
            length = end - start + 1

            with open(file_path, "rb") as f:
                f.seek(start)
                data = f.read(length)

            response = HttpResponse(content=data, status=206, content_type="video/mp4")
            response["Content-Length"] = str(length)
            response["Content-Range"] = f"bytes {start}-{end}/{file_size}"
            response["Accept-Ranges"] = "bytes"
            return response
        except Exception as e:
            return HttpResponse(status=400, content=f"Invalid Range: {str(e)}")
