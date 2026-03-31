from rest_framework import serializers

from app.models.order import Region, District
from odoo.serializers.custom_base_serializer import (
    BaseOdooIDSerializer,
    Base64ImageField,
)
from user.models import UserInfo, User, Address


class UserInfoSerializer(serializers.ModelSerializer):
    avatar = Base64ImageField(required=False, allow_null=True)

    class Meta:
        model = UserInfo
        fields = [
            "id",
            "first_name",
            "last_name",
            "address",
            "avatar",
            "birth_date",
            "gender",
            "referral_link",
            "referral_count",
        ]


class UserSerializer(serializers.ModelSerializer):
    info = UserInfoSerializer(required=False)
    email = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "odoo_id",
            "sync_status",
            "phone",
            "email",
            "role",
            "is_active",
            "is_staff",
            "is_superuser",
            "info",
            "send_odoo",
        ]
        extra_kwargs = {
            "phone": {"validators": []},  # model validatorni chetlab o‘tish uchun
        }

    def get_email(self, obj):
        if obj.phone:
            cleaned_phone = obj.phone.replace("+", "")
            return f"{cleaned_phone}@gmail.com"
        return None

    def validate_phone(self, value):
        value = value.replace(" ", "")
        if not value.startswith("+998") or len(value) != 13 or not value[1:].isdigit():
            raise serializers.ValidationError(
                "Telefon raqam formati noto‘g‘ri. +998XXXXXXXXX ko‘rinishida bo‘lishi kerak."
            )

        if self.instance:
            # update holati, agar o‘zgarmagan bo‘lsa ruxsat
            if self.instance.phone == value:
                return value

        if User.objects.filter(phone=value).exists():
            raise serializers.ValidationError(
                "Bu raqam bilan foydalanuvchi allaqachon mavjud."
            )
        return value

    def create(self, validated_data):
        info_data = validated_data.pop("info", None)
        user = User.objects.create(**validated_data)
        if info_data:
            UserInfo.objects.update_or_create(user=user, defaults=info_data)
        return user

    def update(self, instance, validated_data):
        info_data = validated_data.pop("info", None)
        instance = super().update(instance, validated_data)
        if info_data:
            UserInfo.objects.update_or_create(user=instance, defaults=info_data)
        return instance


class AddressSerializer(BaseOdooIDSerializer):
    user = serializers.SlugRelatedField(
        queryset=User.objects.all(),
        slug_field="odoo_id",
        allow_null=False,
        required=True,
    )
    region = serializers.SlugRelatedField(
        queryset=Region.objects.all(),
        slug_field="odoo_id",
        allow_null=False,
        required=True,
    )
    district = serializers.SlugRelatedField(
        queryset=District.objects.all(),
        slug_field="odoo_id",
        allow_null=False,
        required=True,
    )

    class Meta:
        model = Address
        fields = "__all__"
