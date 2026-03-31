from rest_framework import serializers
from app.models.notification import Notification, NotificationTemplate
from django.contrib.auth import get_user_model
from django.utils.translation import get_language

User = get_user_model()


class NotificationTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationTemplate
        fields = (
            "id",
            "odoo_id",
            "title",
            "description",
            "condition",
            "created_at",
            "updated_at",
        )


class NotificationSerializer(serializers.ModelSerializer):
    is_read = serializers.SerializerMethodField()
    read_count = serializers.SerializerMethodField()
    title = serializers.SerializerMethodField()
    message = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            "id",
            "odoo_id",
            "title",
            "image",
            "message",
            "created_at",
            "updated_at",
            "is_read",
            "read_count",
        ]

    def get_language_code(self):
        lang = get_language()
        if lang in ["uz", "ru", "en"]:
            return lang
        return "uz"

    def get_title(self, obj):
        lang = self.get_language_code()
        return getattr(obj, f"title_{lang}", None)

    def get_message(self, obj):
        lang = self.get_language_code()
        return getattr(obj, f"message_{lang}", None)

    def get_is_read(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return request.user in obj.read_users.all()
        return False  # For unauthenticated users, always return False

    def get_read_count(self, obj):
        return obj.read_count

    def update(self, instance, validated_data):
        user = self.context["request"].user
        if user in instance.send_users.all():
            instance.read_users.add(user)
            instance.save()
        return instance
