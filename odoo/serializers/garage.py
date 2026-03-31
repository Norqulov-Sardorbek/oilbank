from django.contrib.auth import get_user_model
from rest_framework import serializers

from app.models import Branch, Order
from app.models.garage import (
    SomeColor,
    CarColor,
    Car,
    OilChangedHistory,
    Firm,
    CarModel,
)
from app.models.product import OilBrand, FilterBrand
from odoo.serializers.custom_base_serializer import (
    BaseOdooIDSerializer,
    Base64ImageField,
)

User = get_user_model()


class FirmSerializer(BaseOdooIDSerializer):
    class Meta:
        model = Firm
        fields = ["id", "odoo_id", "name", "created_at", "updated_at", "send_odoo"]


class CarModelSerializer(BaseOdooIDSerializer):
    firm = serializers.SlugRelatedField(
        queryset=Firm.objects.all(),
        slug_field="odoo_id",
        allow_null=True,
        required=False,
    )

    class Meta:
        model = CarModel
        fields = [
            "id",
            "odoo_id",
            "name",
            "firm",
            "created_at",
            "updated_at",
            "send_odoo",
        ]


class SomeColorSerializer(BaseOdooIDSerializer):
    class Meta:
        model = SomeColor
        fields = [
            "id",
            "odoo_id",
            "name_en",
            "name_uz",
            "name_ru",
            "color_code",
            "created_at",
            "updated_at",
            "send_odoo",
        ]


class CarColorSerializer(BaseOdooIDSerializer):
    some_color = serializers.SlugRelatedField(
        queryset=SomeColor.objects.all(),
        slug_field="odoo_id",
        allow_null=True,
        required=False,
    )
    car_model = serializers.SlugRelatedField(
        queryset=CarModel.objects.all(),
        slug_field="odoo_id",
    )
    image = Base64ImageField(required=False, allow_null=True)

    class Meta:
        model = CarColor
        fields = [
            "id",
            "odoo_id",
            "some_color",
            "car_model",
            "image",
            "created_at",
            "updated_at",
            "send_odoo",
        ]


class CarSerializer(BaseOdooIDSerializer):
    user = serializers.SlugRelatedField(
        queryset=User.objects.all(),
        slug_field="odoo_id",
        allow_null=True,
        required=False,
    )
    firm = serializers.SlugRelatedField(
        queryset=Firm.objects.all(),
        slug_field="odoo_id",
        allow_null=True,
        required=False,
    )
    model = serializers.SlugRelatedField(
        queryset=CarModel.objects.all(),
        slug_field="odoo_id",
        allow_null=True,
        required=False,
    )
    color = serializers.SlugRelatedField(
        queryset=CarColor.objects.all(),
        slug_field="odoo_id",
        allow_null=True,
        required=False,
    )

    class Meta:
        model = Car
        fields = [
            "id",
            "odoo_id",
            "user",
            "number",
            "firm",
            "model",
            "color",
            "created_at",
            "updated_at",
            "send_odoo",
        ]


class OptionalSlugRelatedField(serializers.SlugRelatedField):
    """SlugRelatedField that returns None if object not found instead of raising error"""
    def to_internal_value(self, data):
        if data is None:
            return None
        queryset = self.get_queryset()
        try:
            return queryset.get(**{self.slug_field: data})
        except queryset.model.DoesNotExist:
            # Return None if object not found instead of raising error
            return None
        except (TypeError, ValueError):
            self.fail('invalid')


class OilChangedHistorySerializer(serializers.ModelSerializer):
    car = serializers.SlugRelatedField(
        queryset=Car.objects.all(),
        slug_field="odoo_id",
        allow_null=True,
        required=False,
    )
    oil_brand = OptionalSlugRelatedField(
        queryset=OilBrand.objects.all(),
        slug_field="odoo_id",
        allow_null=True,
        required=False,
    )
    order = OptionalSlugRelatedField(
        queryset=Order.objects.all(),
        slug_field="odoo_id",
        allow_null=True,
        required=False,
    )
    branch = OptionalSlugRelatedField(
        queryset=Branch.objects.all(),
        slug_field="odoo_id",
        allow_null=True,
        required=False,
    )
    filter_brand = OptionalSlugRelatedField(
        queryset=FilterBrand.objects.all(),
        slug_field="odoo_id",
        allow_null=True,
        required=False,
    )

    class Meta:
        model = OilChangedHistory
        fields = "__all__"
