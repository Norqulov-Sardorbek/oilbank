from django.utils.translation import get_language
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from datetime import timedelta, datetime
from django.core.exceptions import ValidationError

from app.models import Branch
from app.models.garage import (
    Car,
    OilChangedHistory,
    Firm,
    CarModel,
    CarColor,
    OilChangeRating,
    RatingType,
)
from app.serializers.order import OrderDetailSerializer
from app.serializers.product import OilBrandSerializer, FilterBrandSerializer
from app.utils.validators import is_valid_uz_car_number
from dateutil.relativedelta import relativedelta
from django.contrib.auth import get_user_model

User = get_user_model()


class OilChangeRatingSerializer(serializers.ModelSerializer):
    options_ids = serializers.PrimaryKeyRelatedField(
        queryset=RatingType.objects.all(), many=True, required=False
    )
    reviewer = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = OilChangeRating
        fields = [
            "id",
            "reviewer",
            "oil_change_id",
            "rating",
            "description",
            "options_ids",
            "created_at",
        ]
        read_only_fields = ["reviewer", "created_at"]

    def validate(self, data):
        request = self.context.get("request")
        oil_change_id = data.get("oil_change_id")
        rating = int(data.get("rating"))
        if rating < 1 or rating > 5:
            raise ValidationError("Rating over ranged it should be from 1 to 5 ")

        if oil_change_id.car.user != request.user:
            raise ValidationError("You can only rate your own oilchange")

        if OilChangeRating.objects.filter(
            reviewer=request.user, oil_change_id=oil_change_id
        ).exists():
            raise ValidationError("You have already rated this oilchange")

        return data

    def create(self, validated_data):
        validated_data["reviewer"] = self.context["request"].user
        return super().create(validated_data)

    def to_representation(self, instance):
        from .order import RatingTypeSerilazier

        data = super().to_representation(instance)
        # Convert options_ids to full serialized objects for output
        data["options_ids"] = RatingTypeSerilazier(
            instance.options_ids.all(), many=True, context=self.context
        ).data
        return data


class CarCreateSerializer(serializers.ModelSerializer):
    """
    Yangi mashina yaratish uchun serializer.
    `user` maydoni avtomatik `request.user` bo‘lishi uchun, uni ModelSerializer dan olib tashladik.
    """

    color = serializers.PrimaryKeyRelatedField(
        queryset=CarColor.objects.all(), required=False
    )
    firm = serializers.PrimaryKeyRelatedField(queryset=Firm.objects.all())
    model = serializers.PrimaryKeyRelatedField(queryset=CarModel.objects.all())

    class Meta:
        model = Car
        fields = ["id", "odoo_id", "number", "firm", "model", "color"]

    def validate_number(self, value):
        if not is_valid_uz_car_number(value):
            raise serializers.ValidationError(
                _("Car number is not valid in Uzbekistan")
            )
        return value

    def create(self, validated_data):
        validated_data["user"] = self.context[
            "request"
        ].user  # Foydalanuvchini avtomatik qo‘shish
        return super().create(validated_data)


class CarUpdateSerializer(serializers.ModelSerializer):
    """
    Mashina ma‘lumotlarini yangilash uchun serializer.
    `user` maydoni talab qilinmaydi.
    """

    color = serializers.PrimaryKeyRelatedField(
        queryset=CarColor.objects.all(), required=False
    )
    firm = serializers.PrimaryKeyRelatedField(queryset=Firm.objects.all())
    model = serializers.PrimaryKeyRelatedField(queryset=CarModel.objects.all())

    class Meta:
        model = Car
        fields = ["odoo_id", "number", "firm", "model", "color"]


class CarColorSerializer(serializers.ModelSerializer):
    color = serializers.SerializerMethodField(read_only=True)
    color_code = serializers.SerializerMethodField(read_only=True)

    def get_color_code(self, obj):
        return obj.some_color.color_code

    class Meta:
        model = CarColor
        fields = ["id", "color", "car_model", "image", "color_code"]

    def get_color(self, obj):
        lang = get_language()
        if lang == "ru":
            return obj.some_color.name_ru
        elif lang == "uz":
            return obj.some_color.name_uz
        return obj.some_color.name_en


class CarShortSerializer(serializers.ModelSerializer):
    model = serializers.ReadOnlyField(source="model.name")
    firm = serializers.ReadOnlyField(source="firm.name")

    class Meta:
        model = Car
        fields = ["id", "number", "firm", "model"]


class BranchShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = ["id", "name"]


# change


class OilChangedHistorySerializer(serializers.ModelSerializer):
    """
    Serializer for displaying oil change history with accurate remaining time calculations.
    """

    months_left = serializers.SerializerMethodField(read_only=True)
    days_left = serializers.SerializerMethodField(read_only=True)
    percentage_time_passed = serializers.SerializerMethodField(read_only=True)
    next_oil_change_date = serializers.SerializerMethodField(read_only=True)
    oil_brand_detail = OilBrandSerializer(read_only=True, source="oil_brand")
    filter_brand_detail = FilterBrandSerializer(read_only=True, source="filter_brand")
    car_detail = CarShortSerializer(read_only=True, source="car")
    branch_detail = BranchShortSerializer(read_only=True, source="branch")
    given_rating = serializers.SerializerMethodField()
    has_rated = serializers.SerializerMethodField()
    has_related_order = serializers.SerializerMethodField()
    related_order_check_detail = serializers.SerializerMethodField()

    class Meta:
        model = OilChangedHistory
        fields = [
            "id",
            "odoo_id",
            "car",
            "car_detail",
            "last_oil_change",
            "distance",
            "order",
            "oil_brand",
            "recommended_distance",
            "daily_distance",
            "months_left",
            "days_left",
            "branch_detail",
            "percentage_time_passed",
            "next_oil_change_date",
            "duration_days",
            "oil_brand_detail",
            "filter_changed",
            "filter_brand_detail",
            "note",
            "created_at",
            "updated_at",
            "given_rating",
            "has_rated",
            "related_order_check_detail",
            "has_related_order",
        ]
        read_only_fields = [
            "months_left",
            "days_left",
            "percentage_time_passed",
            "next_oil_change_date",
            "oil_brand_detail",
            "filter_changed",
            "filter_brand_detail",
            "has_rated",
            "given_rating",
            "note",
        ]

    def get_related_order_check_detail(self, obj):
        return OrderDetailSerializer(obj.order, context=self.context).data.get("check_xml")

    def get_has_related_order(self, obj):
        return bool(obj.order)

    def get_has_rated(self, obj):
        request = self.context.get("request")
        if (
            not request
            or not hasattr(request, "user")
            or not request.user.is_authenticated
        ):
            return False
        return OilChangeRating.objects.filter(
            reviewer=request.user, oil_change_id=obj
        ).exists()

    def get_given_rating(self, obj):

        request = self.context.get("request")
        if (
            not request
            or not hasattr(request, "user")
            or not request.user.is_authenticated
        ):
            return None
        rating = OilChangeRating.objects.filter(
            reviewer=request.user, oil_change_id=obj
        ).first()
        return (
            OilChangeRatingSerializer(rating, context={"request": request}).data
            if rating
            else None
        )

    def get_days_left(self, obj):
        months, days = self.calculate_month_date(obj)
        return days

    def get_next_oil_change_date(self, obj):
        total_days_for_oil_change = obj.recommended_distance / obj.daily_distance
        next_oil_change_date = obj.last_oil_change.date() + timedelta(
            days=total_days_for_oil_change
        )
        return next_oil_change_date.strftime("%Y-%m-%d")

    def calculate_month_date(self, obj):
        total_days_for_oil_change = obj.recommended_distance / obj.daily_distance
        last_change_date = obj.last_oil_change.date()
        next_oil_change_date = last_change_date + timedelta(
            days=total_days_for_oil_change
        )
        today = datetime.today().date()

        days_left = (next_oil_change_date - today).days
        days_left = max(days_left, 0)
        if days_left <= 0:
            return 0, 0

        temp_future_date = today + timedelta(days=days_left)
        delta = relativedelta(temp_future_date, today)
        months = delta.years * 12 + delta.months
        days = delta.days

        if days < 0:
            temp_date = today + relativedelta(months=+months)
            days = (temp_future_date - temp_date).days

        return months, days

    def get_months_left(self, obj):
        month, days = self.calculate_month_date(obj)
        return month

    def get_percentage_time_passed(self, obj):
        total_days_for_oil_change = obj.recommended_distance / obj.daily_distance
        elapsed_days = (datetime.today().date() - obj.last_oil_change.date()).days
        percentage_passed = (elapsed_days / total_days_for_oil_change) * 100
        remaining_percentage = 100 - round(percentage_passed, 2)
        return max(0, min(100, remaining_percentage))


class CarModelSerializer(serializers.ModelSerializer):

    class Meta:
        model = CarModel
        fields = ["id", "odoo_id", "name", "firm", "created_at", "updated_at"]


class FirmSerializer(serializers.ModelSerializer):

    class Meta:
        model = Firm
        fields = ["id", "odoo_id", "name", "created_at", "updated_at"]


class CarListSerializer(serializers.ModelSerializer):
    """
    Moy almashtirish tarixini va foydalanuvchining boshqa mashinalarini ham chiqaradi.
    """

    color = CarColorSerializer(read_only=True)
    oil_change_history = serializers.SerializerMethodField()
    firm = FirmSerializer(read_only=True)
    model = CarModelSerializer(read_only=True)

    class Meta:
        model = Car
        fields = [
            "id",
            "odoo_id",
            "number",
            "firm",
            "model",
            "color",
            "oil_change_history",
        ]

    def get_oil_change_history(self, obj):
        """
        Ushbu mashinaga tegishli moy almashtirish tarixini chiqaradi.
        """
        history = OilChangedHistory.objects.filter(car=obj)
        return OilChangedHistorySerializer(history, many=True, context=self.context).data
    

class OilChangedHistoryNotificationSerializer(serializers.ModelSerializer):
    """
    Serializer for OilChangedHistory used in notification tasks.
    Only includes fields necessary for creating oil change notifications.
    """
    next_oil_change_date = serializers.SerializerMethodField(read_only=True)
    car = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = OilChangedHistory
        fields = ['id', 'car', 'next_oil_change_date']

    def get_next_oil_change_date(self, obj):
        
        distance = obj.daily_distance
        
        if not distance or distance <= 0:
            distance = 1

        total_days_for_oil_change = obj.recommended_distance / distance
        next_oil_change_date = obj.last_oil_change.date() + timedelta(
            days=total_days_for_oil_change
        )
        return next_oil_change_date.strftime("%Y-%m-%d")
