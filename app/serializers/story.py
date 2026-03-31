from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from app.models.story import Story
from django.utils.translation import get_language
from rest_framework.exceptions import ValidationError
import os


class StoryGetSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    video = serializers.SerializerMethodField()
    caption = serializers.SerializerMethodField()
    is_read = serializers.SerializerMethodField()
    video_size = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Story
        fields = [
            "id",
            "user",
            "image",
            "video",
            "video_size",
            "caption",
            "created_at",
            "expires_at",
            "is_expired",
            "is_read",
            "send_users",
            "date",
            "time",
        ]

    def get_is_read(self, obj):
        user = self.context["request"].user
        return obj.read_users.filter(id=user.id).exists()

    def get_video_size(self, obj):
        language = get_language()
        if language == "ru":
            path = obj.video_ru.path if obj.video_ru else None
        elif language == "uz":
            path = obj.video_uz.path if obj.video_uz else None
        else:
            path = obj.video_en.path if obj.video_en else None

        if path and os.path.exists(path):
            return os.path.getsize(path)
        return 0

    def get_image(self, obj):
        language = get_language()
        if language == "ru":
            return obj.image_ru.url if obj.image_ru else None
        elif language == "uz":
            return obj.image_uz.url if obj.image_uz else None
        return obj.image_en.url if obj.image_en else None

    def get_video(self, obj):
        request = self.context.get("request")
        language = get_language()

        if language == "ru" and obj.video_ru:
            return request.build_absolute_uri(obj.video_ru.url)
        elif language == "uz" and obj.video_uz:
            return request.build_absolute_uri(obj.video_uz.url)
        elif obj.video_en:
            return request.build_absolute_uri(obj.video_en.url)
        return None

    def get_caption(self, obj):
        language = get_language()
        if language == "ru":
            return obj.caption_ru
        elif language == "uz":
            return obj.caption_uz
        return obj.caption_en


class StorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Story
        fields = [
            "id",
            "user",
            "date",
            "time",
            "image_en",
            "image_ru",
            "image_uz",
            "video_en",
            "video_ru",
            "video_uz",
            "caption_en",
            "caption_ru",
            "caption_uz",
            "created_at",
            "expires_at",
            "read_users",
            "send_users",
        ]


class StoryPostSerializer(serializers.ModelSerializer):
    class Meta:
        model = Story
        fields = [
            "id",
            "user",
            "date",
            "time",
            "image_en",
            "image_ru",
            "image_uz",
            "video_en",
            "video_ru",
            "video_uz",
            "caption_en",
            "caption_ru",
            "caption_uz",
            "created_at",
            "expires_at",
            "read_users",
            "send_users",
        ]

    def validate(self, data):
        """
        Custom validation logic for Story fields.
        """
        images = [data.get("image_en"), data.get("image_ru"), data.get("image_uz")]
        videos = [data.get("video_en"), data.get("video_ru"), data.get("video_uz")]
        captions = [
            data.get("caption_en"),
            data.get("caption_ru"),
            data.get("caption_uz"),
        ]

        # Check if at least one field is filled
        if not any(images + videos + captions):
            raise ValidationError(
                _("At least one field must be filled (image, video, or caption).")
            )

        # Check if all image fields are provided when one is used
        if any(images) and not all(images):
            raise ValidationError(
                _("All image fields must be provided if any are filled.")
            )

        # Check if all video fields are provided when one is used
        if any(videos) and not all(videos):
            raise ValidationError(
                _("All video fields must be provided if any are filled.")
            )

        # Check if all caption fields are provided when one is used
        if any(captions) and not all(captions):
            raise ValidationError(
                _("All caption fields must be provided if any are filled.")
            )

        return data
