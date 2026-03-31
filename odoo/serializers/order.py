from datetime import datetime, timedelta
from decimal import Decimal
from django.utils.timezone import make_aware, now

from app.models import Car
from app.models.order import (
    Order,
    OrderItem,
    OrderRating,
    Basket,
    BasketItem,
    Region,
    District,
    DeliveryPrice,
    PromoCode,
    RatingType, 
    LoyaltyProgram, 
    PromoReward,
    LoyaltyRule,
)
from user.models import User, Address
from app.models.company_info import Branch
from app.models.product import Pricelist, Product, Currency, Category
from rest_framework import serializers
from .custom_base_serializer import BaseOdooIDSerializer, Base64ImageField


class ReginSerializer(BaseOdooIDSerializer):
    class Meta:
        model = Region
        fields = "__all__"


class DistrictSerializer(BaseOdooIDSerializer):
    region = serializers.SlugRelatedField(
        queryset=Region.objects.all(),
        slug_field="odoo_id",
    )

    class Meta:
        model = District
        fields = "__all__"


class RatingTypeSerializer(BaseOdooIDSerializer):
    icon = Base64ImageField()

    class Meta:
        model = RatingType
        fields = "__all__"


class OrderRatingSerializer(BaseOdooIDSerializer):
    options = serializers.SlugRelatedField(
        queryset=RatingType.objects.all(),
        slug_field="odoo_id",
    )

    class Meta:
        model = OrderRating
        fields = "__all__"


class DeliveryPriceSerializer(BaseOdooIDSerializer):
    district = serializers.SlugRelatedField(
        queryset=District.objects.all(),
        slug_field="odoo_id",
    )

    class Meta:
        model = DeliveryPrice
        fields = "__all__"


class OrderSerializer(BaseOdooIDSerializer):
    user = serializers.CharField(required=True)
    company_type = serializers.CharField(write_only=True, required=True)
    branch = serializers.SlugRelatedField(
        queryset=Branch.objects.all(),
        slug_field="odoo_id",
        allow_null=True,
        required=False,
    )
    address_id = serializers.SlugRelatedField(
        queryset=Address.objects.all(),
        slug_field="odoo_id",
        allow_null=True,
        required=False,
    )
    promocode = serializers.SlugRelatedField(
        queryset=PromoCode.objects.all(),
        slug_field="odoo_id",
        allow_null=True,
        required=False,
    )
    pricelist = serializers.SlugRelatedField(
        queryset=Pricelist.objects.all(),
        slug_field="odoo_id",
        allow_null=True,
        required=False,
    )

    amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, default=0, required=False
    )

    class Meta:
        model = Order
        fields = "__all__"

    def validate(self, attrs):
        pickup_time = attrs.get("pickup_time")
        order_type = attrs.get("type")
        # Check if this is an update (self.instance exists)
        is_update = self.instance is not None

        if not (is_update and order_type is None):
            if order_type == "DELIVERY":
                if not attrs.get("address_id"):
                    raise serializers.ValidationError(
                        "Address is required for delivery orders"
                    )
            elif order_type == "PICKUP":
                if not attrs.get("branch"):
                    raise serializers.ValidationError(
                        "Branch is required for pickup orders"
                    )

        if pickup_time and not isinstance(pickup_time, datetime):
            now_dt = make_aware(datetime.now())
            tomorrow = (now_dt + timedelta(days=1)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            if pickup_time < tomorrow:
                raise serializers.ValidationError(
                    "Pickup time must be at least tomorrow"
                )

        status = attrs.get("status")
        payment_status = attrs.get("payment_status")
        
        if is_update:
            current_status = status if status is not None else self.instance.status
            current_payment_status = payment_status if payment_status is not None else self.instance.payment_status
        else:
            current_status = status
            current_payment_status = payment_status
            
        if current_status == "COMPLETED" and current_payment_status != "COMPLETED":
            raise serializers.ValidationError({
                "message": "Order status cannot be COMPLETED without payment status being COMPLETED"
            })

        amount = attrs.get("amount", 0)
        user = attrs.get("user")
        company_type = attrs.pop("company_type", None)
        if company_type == "person":
            try:
                user = User.objects.get(odoo_id=user)
            except User.DoesNotExist:
                raise serializers.ValidationError(
                    "User with this odoo_id does not exist"
                )
            attrs["user"] = user
        elif company_type == "car":
            try:
                car = Car.objects.get(odoo_id=user)
            except Car.DoesNotExist:
                raise serializers.ValidationError(
                    "Car with this odoo_id does not exist"
                )
            attrs["car"] = car
            attrs["user"] = car.user
        else:
            raise serializers.ValidationError("Invalid company type")
        attrs.pop("company_type", None)
        return attrs

    def create(self, validated_data):
        amount = validated_data.pop('amount', 0)
        price = validated_data.pop('price', 0)
        balance_amount = price - amount
        order = Order(**validated_data)
        order.price = price
        order.balance_amount = balance_amount
        order.save()
        return order

    def update(self, instance, validated_data):
        amount = validated_data.pop('amount', 0)
        price = validated_data.pop('price', 0)
        balance_amount = price - amount
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.price = price
        instance.balance_amount = balance_amount
        instance.save()
        return instance


class OrderItemSerializer(BaseOdooIDSerializer):
    order = serializers.SlugRelatedField(
        queryset=Order.objects.all(), slug_field="odoo_id"
    )
    product = serializers.SlugRelatedField(
        queryset=Product.objects.all(), slug_field="odoo_id"
    )

    class Meta:
        model = OrderItem
        fields = "__all__"

    def validate(self, data):
        quantity = data.get('quantity')
        price = data.get('price')
        total_price = data.get('total_price')

        if quantity and price and total_price:
            # Calculate total discount amount
            total_discount = Decimal(quantity) * Decimal(price) - Decimal(total_price)
            data['discount_amount'] = total_discount

            # Calculate discount percentage
            if price > 0:
                discount_percent = (total_discount / (Decimal(quantity) * Decimal(price))) * 100
                data['discount_percent'] = float(discount_percent)
            else:
                data['discount_percent'] = 0.0

        return data

class LoyaltyProgramSerializer(BaseOdooIDSerializer):
    branch = serializers.SlugRelatedField(
        queryset=Branch.objects.all(),
        slug_field="odoo_id",
        allow_null=True,
        required=False
    )
    currency = serializers.SlugRelatedField(
        queryset=Currency.objects.all(),
        slug_field="odoo_id"
    )
    class Meta:
        model = LoyaltyProgram
        fields = "__all__"


class PromoRewardSerializer(BaseOdooIDSerializer):
    program = serializers.SlugRelatedField(
        queryset=LoyaltyProgram.objects.all(),
        slug_field="odoo_id"
    )
    discount_line_product = serializers.SlugRelatedField(
        queryset=Product.objects.all(),
        slug_field="odoo_id",
        allow_null=True,
        required=False
    )
    discount_product_ids = serializers.SlugRelatedField(
        queryset=Product.objects.all(),
        slug_field="odoo_id",
        many=True,
        allow_null=True,
        required=False
    )
    discount_product_category_id = serializers.SlugRelatedField(
        queryset=Category.objects.all(),
        slug_field="odoo_id",
        allow_null=True,
        required=False
    )
    class Meta:
        model = PromoReward
        fields = "__all__"


class PromoCodeSerializer(BaseOdooIDSerializer):
    program = serializers.SlugRelatedField(
        queryset=LoyaltyProgram.objects.all(),
        slug_field="odoo_id"
    )

    partner = serializers.SlugRelatedField(
        queryset=User.objects.all(),
        slug_field="odoo_id",
        allow_null=True,
        required=False
    )
    class Meta:
        model = PromoCode
        fields = "__all__"


class LoyaltyRuleSerializer(BaseOdooIDSerializer):
    program = serializers.SlugRelatedField(
        queryset=LoyaltyProgram.objects.all(),
        slug_field="odoo_id",
        allow_null=True,
        required=False
    )

    product = serializers.SlugRelatedField(
        queryset=Product.objects.all(),
        slug_field="odoo_id",
        allow_null=True,
        required=False
    )

    category = serializers.SlugRelatedField(
        queryset=Category.objects.all(),
        slug_field="odoo_id",
        allow_null=True,
        required=False
    )

    class Meta:
        model = LoyaltyRule
        fields = "__all__"
