# serializers.py
from rest_framework import serializers
from user.models import User
from app.models.story import Story
from .custom_base_serializer import BaseOdooIDSerializer, Base64ImageField, Base64FileField


class StorySerializer(BaseOdooIDSerializer):
    # media (optional per locale)
    image_en = Base64ImageField(required=False, allow_null=True)
    image_ru = Base64ImageField(required=False, allow_null=True)
    image_uz = Base64ImageField(required=False, allow_null=True)

    video_en = Base64FileField(required=False, allow_null=True)
    video_ru = Base64FileField(required=False, allow_null=True)
    video_uz = Base64FileField(required=False, allow_null=True)

    # relations by odoo_id
    user = serializers.SlugRelatedField(
        queryset=User.objects.all(),
        slug_field="odoo_id",
        required=True,
    )
    read_users = serializers.SlugRelatedField(
        queryset=User.objects.all(),
        slug_field="odoo_id",
        many=True,
        required=False,
        allow_null=True,
    )
    send_users = serializers.SlugRelatedField(
        queryset=User.objects.all(),
        slug_field="odoo_id",
        many=True,
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Story
        fields = "__all__"

    def validate(self, attrs):
        # Merge with instance for partial updates
        data = {} if not self.instance else {
            "expires_at": self.instance.expires_at,
        }
        data.update(attrs)

        # Basic check: expires_at present and in the future (optional but sensible)
        expires_at = data.get("expires_at")
        if expires_at is None:
            raise serializers.ValidationError({"expires_at": "expires_at is required."})
        return attrs
