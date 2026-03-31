from django.db.models import Q
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.decorators import action
from app.models.notification import Notification, NotificationTemplate
from app.serializers import notification
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiExample
from drf_spectacular.types import OpenApiTypes
from django.utils.translation import gettext_lazy as _


@extend_schema_view(
    list=extend_schema(
        summary="List notification templates",
        description="Returns notification templates available to the authenticated user",
        responses={200: notification.NotificationTemplateSerializer(many=True)},
    ),
    retrieve=extend_schema(
        summary="Retrieve notification template",
        description="Returns details of a specific notification template",
        responses={200: notification.NotificationTemplateSerializer},
    ),
    create=extend_schema(
        summary="Create notification template",
        description="Creates a new notification template (admin only)",
        request=notification.NotificationTemplateSerializer,
        responses={201: notification.NotificationTemplateSerializer},
    ),
    update=extend_schema(
        summary="Update notification template",
        description="Updates all fields of a notification template (admin only)",
        request=notification.NotificationTemplateSerializer,
        responses={200: notification.NotificationTemplateSerializer},
    ),
    partial_update=extend_schema(
        summary="Partial update notification template",
        description="Updates selected fields of a notification template (admin only)",
        request=notification.NotificationTemplateSerializer,
        responses={200: notification.NotificationTemplateSerializer},
    ),
    destroy=extend_schema(
        summary="Delete notification template",
        description="Removes a notification template (admin only)",
        responses={204: None},
    ),
)
class NotificationTemplateViewSet(viewsets.ModelViewSet):
    queryset = NotificationTemplate.objects.all()
    serializer_class = notification.NotificationTemplateSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return NotificationTemplate.objects.filter(send_users=self.request.user)


@extend_schema_view(
    list=extend_schema(
        summary="List notifications",
        description="Returns notifications sent to the authenticated user",
        responses={200: notification.NotificationSerializer(many=True)},
    ),
    retrieve=extend_schema(
        summary="Retrieve notification",
        description="Returns details of a specific notification",
        responses={200: notification.NotificationSerializer},
    ),
    create=extend_schema(
        summary="Create notification",
        description="Creates a new notification (admin only)",
        request=notification.NotificationSerializer,
        responses={201: notification.NotificationSerializer},
    ),
    update=extend_schema(
        summary="Update notification",
        description="Updates all fields of a notification (admin only)",
        request=notification.NotificationSerializer,
        responses={200: notification.NotificationSerializer},
    ),
    partial_update=extend_schema(
        summary="Partial update notification",
        description="Updates selected fields of a notification (admin only)",
        request=notification.NotificationSerializer,
        responses={200: notification.NotificationSerializer},
    ),
    destroy=extend_schema(
        summary="Delete notification",
        description="Removes a notification (admin only)",
        responses={204: None},
    ),
)
class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all()
    serializer_class = notification.NotificationSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        if self.request.user.is_authenticated:
            return Notification.objects.filter(
                Q(send_users=self.request.user) | Q(send_users__isnull=True)
            ).distinct()
        return Notification.objects.filter(send_users__isnull=True)

    @extend_schema(
        summary="Mark notification as read",
        description="Marks a specific notification as read by the current user",
        responses={200: OpenApiTypes.OBJECT, 403: OpenApiTypes.OBJECT},
        examples=[
            OpenApiExample(
                "Success Response",
                value={"status": "Notification marked as read"},
                response_only=True,
                status_codes=["200"],
            ),
            OpenApiExample(
                "Error Response",
                value={
                    "status": "You are not authorized to mark this notification as read"
                },
                response_only=True,
                status_codes=["403"],
            ),
        ],
    )
    @action(detail=True, methods=["patch"], permission_classes=[IsAuthenticated])
    def mark_as_read(self, request, pk=None):
        if not request.user.is_authenticated:
            # Return empty 200 response for unauthenticated users
            return Response(status=200)

        notification_obj = self.get_object()
        user = request.user
        if (
            notification_obj.send_users.count() == 0
            or user in notification_obj.send_users.all()
        ):
            notification_obj.read_users.add(user)
            notification_obj.save()
            return Response({"status": _("Notification marked as read")})
        else:
            return Response(
                {"status": "You are not authorized to mark this notification as read"},
                status=403,
            )

    @action(detail=False, methods=['put'], permission_classes=[IsAuthenticated])
    def mark_all_as_read(self, request):
        notifications = Notification.objects.filter(Q(send_users=request.user) | Q(send_users__isnull=True))
        for notification in notifications:
            notification.read_users.add(request.user)
            notification.save()
        return Response({"status": _("All notifications marked as read")})

    @extend_schema(
        summary="List unread notifications",
        description="Returns all unread notifications for the authenticated user",
        responses={200: notification.NotificationSerializer(many=True)},
    )
    @action(detail=False, methods=["get"])
    def unread(self, request):
        notifications = Notification.objects.filter(send_users=request.user).exclude(
            read_users=request.user
        )
        serializer = notification.NotificationSerializer(
            notifications, many=True, context={"request": request}
        )
        return Response(serializer.data)
