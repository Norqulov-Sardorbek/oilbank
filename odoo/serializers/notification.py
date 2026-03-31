from rest_framework import serializers
from app.models.notification import Notification, NotificationTemplate


class NotificationTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationTemplate
        fields = "__all__"


class NotificationSerializer(serializers.ModelSerializer):
    read_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Notification
        fields = "__all__"
