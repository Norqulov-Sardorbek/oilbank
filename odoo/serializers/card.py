from decimal import Decimal, ROUND_DOWN

from app.models import Order
from .custom_base_serializer import BaseOdooIDSerializer, Base64ImageField
from app.models.card import BalanceStatus, Balance, Cashback
from rest_framework import serializers
from user.models import User


class BalanceStatusSerializer(BaseOdooIDSerializer):
    icon = Base64ImageField(required=False, allow_null=True)

    class Meta:
        model = BalanceStatus
        fields = "__all__"


class BalanceSerializer(BaseOdooIDSerializer):
    user = serializers.SlugRelatedField(
        queryset=User.objects.all(),
        slug_field="odoo_id",
        required=False,
        allow_null=True,
    )
    balance_status = serializers.SlugRelatedField(
        queryset=BalanceStatus.objects.all(),
        slug_field="odoo_id",
        required=False,
        allow_null=True,
    )
    balance = serializers.DecimalField(max_digits=16, decimal_places=2)
    total_sales = serializers.DecimalField(max_digits=16, decimal_places=2)

    class Meta:
        model = Balance
        fields = "__all__"

    def to_internal_value(self, data):
        if "balance" in data:
            data["balance"] = str(Decimal(data["balance"]).quantize(Decimal("0.01"), rounding=ROUND_DOWN))
        if "total_sales" in data:
            data["total_sales"] = str(Decimal(data["total_sales"]).quantize(Decimal("0.01"), rounding=ROUND_DOWN))
        return super().to_internal_value(data)


class CashbackSerializer(BaseOdooIDSerializer):
    order = serializers.SlugRelatedField(
        queryset=Order.objects.all(),
        slug_field="odoo_id",
        required=False,
        allow_null=True,
    )
    balance = serializers.SlugRelatedField(
        queryset=Balance.objects.all(),
        slug_field="odoo_id",
        required=False,
        allow_null=True,
    )
    

    class Meta:
        model = Cashback
        fields = "__all__"
