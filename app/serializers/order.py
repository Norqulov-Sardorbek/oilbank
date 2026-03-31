from django.utils import timezone
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from app.models.card import Cashback
from app.models.order import *
from app.serializers.company_info import BranchSerializer, BranchOutputSerializer
from django.utils.translation import gettext_lazy as _, get_language
from datetime import datetime, timedelta
from django.utils.timezone import make_aware
from user.models import Address, User
from app.serializers.product import ProductShortSerializer


# for order detail serializer
class LoyaltyCardDataSerializer(serializers.Serializer):
    loyalty = serializers.CharField(
        required=False, allow_null=True, help_text="Loyalty level name"
    )
    percentage = serializers.FloatField(
        required=False, allow_null=True, help_text="Cashback percentage"
    )
    amount = serializers.DecimalField(
        required=False,
        allow_null=True,
        max_digits=10,
        decimal_places=2,
        help_text="Cashback amount earned",
    )
    used_amount = serializers.DecimalField(
        required=False,
        allow_null=True,
        max_digits=10,
        decimal_places=2,
        help_text="Used cashback amount",
    )


# region
class RegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Region
        fields = ["id", "name", "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]


# district
class DistrictSerializer(serializers.ModelSerializer):
    delivery_price = serializers.SerializerMethodField()

    class Meta:
        model = District
        fields = ["id", "region", "name", "created_at", "updated_at", "delivery_price"]
        read_only_fields = ["created_at", "updated_at", "delivery_price"]

    def get_delivery_price(self, obj):
        delivery_price = DeliveryPrice.objects.filter(district=obj).first()
        if delivery_price:
            return delivery_price.price
        return 0.00


# Basket
class AddressReadSerializer(serializers.ModelSerializer):
    delivery_price = serializers.SerializerMethodField(read_only=True)
    region = RegionSerializer(read_only=True)
    district = DistrictSerializer(read_only=True)

    class Meta:
        model = Address
        fields = [
            "id",
            "user",
            "name",
            "region",
            "district",
            "additional",
            "yandex_link",
            "delivery_price",
            "building",
            "floor",
            "demophone_code",
            "is_main",
        ]

    def get_delivery_price(self, instance):
        from app.models.order import DeliveryPrice

        delivery_price = DeliveryPrice.objects.filter(
            district=instance.district
        ).first()
        return delivery_price.price if delivery_price else 0.00


class BasketSerializer(serializers.ModelSerializer):

    class Meta:
        model = Basket
        fields = "__all__"


class BasketUpdateSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=0)

    def validate_product_id(self, value):
        from app.models import Product  # Adjust to your actual app path

        if not Product.objects.filter(id=value).exists():
            raise serializers.ValidationError("Product does not exist.")
        return value


class BasketBulkUpdateSerializer(serializers.Serializer):
    items = BasketUpdateSerializer(many=True)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("Items list cannot be empty.")
        return value


class BasketItemSerializer(serializers.ModelSerializer):
    product = ProductShortSerializer(read_only=True)
    
    class Meta:
        model = BasketItem
        fields = [
            "id",
            "product",
            "quantity",
            "price",
            "total_price",
            "discount_amount",
            "discount_percent",
        ]
        read_only_fields = [
            "price",
            "total_price",
            "discount_amount",
            "discount_percent",
        ]


class BasketGetSerializer(serializers.ModelSerializer):
    items = serializers.SerializerMethodField()  # Source is items.all

    class Meta:
        model = Basket
        fields = ["id", "items", "price", "created_at"]
        read_only_fields = ["price", "created_at"]

    def get_items(self, obj):
        # Order items by id to maintain insertion order
        items = obj.items.all().order_by("-id")
        return BasketItemSerializer(items, many=True).data


class OrderUpdateSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    order_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=0)

    def validate_product_id(self, value):
        from app.models import Product  # Adjust to your actual app path

        if not Product.objects.filter(id=value).exists():
            raise serializers.ValidationError("Product does not exist.")
        return value

    def validate_order_id(self, value):
        if not Order.objects.filter(id=value).exists():
            raise serializers.ValidationError("Order does not exist")
        return value


class OrderSerializer(serializers.ModelSerializer):
    address_id = AddressReadSerializer(read_only=True)
    region = RegionSerializer(read_only=True)
    district = DistrictSerializer(read_only=True)

    class Meta:
        model = Order
        fields = "__all__"

class OrderNotificationSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source="user.id")
    car_plate = serializers.CharField(source="car.number", default=None)
    car_model = serializers.CharField(source="car.model", default=None)
    branch_name = serializers.CharField(source="branch.name", default=None)
    region = serializers.CharField(source="region.name", default=None)
    district = serializers.CharField(source="district.name", default=None)

    class Meta:
        model = Order
        fields = [
            'id', 'status', 'name', 'uuid', 'price', 'user_id', 'car_plate',
            'car_model', 'branch_name', 'region', 'district', 'created_at',
        ]


class OrderItemSerializer(serializers.ModelSerializer):
    product = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "product",
            "quantity",
            "price",
            "total_price",
            "discount_amount",
            "discount_percent",
        ]

    def get_product(self, obj):
        serializer = ProductShortSerializer(obj.product, context=self.context)
        return serializer.data


class OrderGetSerializer(serializers.ModelSerializer):
    order_items = serializers.SerializerMethodField()
    region = RegionSerializer()
    district = DistrictSerializer()
    address_id = AddressReadSerializer()

    class Meta:
        model = Order
        fields = [
            "id",
            "odoo_id",
            "user",
            "type",
            "status",
            "payment_status",
            "payment_method",
            "created_at",
            "price",
            "branch",
            "region",
            "district",
            "address_id",
            "description",
            "promocode",
            "order_items",
            "cancelled_at",
            "completed_at",
            "updated_at",
            "source",
        ]

    def get_order_items(self, obj):
        order_items = OrderItem.objects.filter(
            order=obj,
            product__product_type="PRODUCT"  # Exclude cashback items
            )
        return OrderItemSerializer(order_items, many=True).data


class OrderCreateSerializer(serializers.ModelSerializer):
    promocode = serializers.CharField(required=False)
    address_id = serializers.PrimaryKeyRelatedField(
        queryset=Address.objects.all(), write_only=True, allow_null=True, required=False
    )
    use_balance = serializers.BooleanField(default=False, required=False)
    balance_amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, default=0.0, min_value=0
    )
    secondary_payment_method = serializers.ChoiceField(
        choices=[
            "CLICK",
            "XAZNA",
            "ALIF",
            "BEEPUL",
            "ANORBANK",
            "OSON",
            "PAYME",
            "UZUM",
            "CARD",
            "ON_RECEIVE",
            "CASH",
        ],
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Order
        fields = [
            "type",
            "payment_method",
            "branch",
            "address_id",
            "description",
            "pickup_time",
            "promocode",
            "use_balance",
            "balance_amount",
            "secondary_payment_method",
            "source",
        ]

    def validate(self, attrs):
        # Validate order type and required fields
        if attrs["type"] == "PICKUP" and not attrs.get("branch"):
            raise serializers.ValidationError(
                {"branch": _("Branch is required for pickup orders")}
            )

        if attrs["type"] == "DELIVERY" and not attrs.get("address_id"):
            raise serializers.ValidationError(
                {"location": _("Address is required for delivery orders")}
            )

        if attrs["type"] == "DELIVERY":
            attrs["branch"] = Branch.objects.filter(branch_type="ONLINE").first()

        # Validate payment method
        valid_payment_methods = [
            "CLICK",
            "XAZNA",
            "ALIF",
            "BEEPUL",
            "ANORBANK",
            "OSON",
            "PAYME",
            "CARD",
            "CASH",
            "UZUM",
            "ON_RECEIVE",
            "CASHBACK",
            "MIXED",
        ]
        if (
            attrs.get("payment_method")
            and attrs.get("payment_method") not in valid_payment_methods
        ):
            raise serializers.ValidationError(
                {
                    "payment_method": _(
                        "Invalid payment method. Choose from {}"
                    ).format(", ".join(valid_payment_methods))
                }
            )

        # Validate balance usage
        if attrs.get("use_balance"):
            if attrs.get("payment_method") not in [
                "CASHBACK",
                "MIXED",
            ]:
                raise serializers.ValidationError(
                    {
                        "payment_method": _(
                            "Balance can only be used with CASHBACK or MIXED"
                        )
                    }
                )
            if attrs.get("balance_amount") <= 0:
                raise serializers.ValidationError(
                    {
                        "balance_amount": _(
                            "Balance amount must be greater than 0 when use_balance is True"
                        )
                    }
                )

        # Validate mixed payment
        if attrs.get("payment_method") == "MIXED" and not attrs.get(
            "secondary_payment_method"
        ):
            raise serializers.ValidationError(
                {
                    "secondary_payment_method": _(
                        "Secondary payment method is required for MIXED payments"
                    )
                }
            )

        # Validate pickup time
        pickup_time = attrs.get("pickup_time")
        if attrs["type"] == "PICKUP" and not pickup_time:
            raise serializers.ValidationError(
                {"pickup_time": _("Pickup time is required for pickup orders")}
            )
        if pickup_time and not isinstance(pickup_time, datetime):
            now = make_aware(datetime.now())
            tomorrow = (now + timedelta(days=1)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            if pickup_time < tomorrow:
                raise serializers.ValidationError(
                    {"pickup_time": _("Pickup time must be at least tomorrow")}
                )

        return attrs

    def validate_promocode(self, value):
        user = self.context["request"].user
        today = timezone.now().date()

        promo_code = PromoCode.objects.filter(
            code=value.strip(),
            active=True,
        ).select_related("program").first()

        if not promo_code:
            raise serializers.ValidationError(_("Invalid promo code"))

        if promo_code.partner and promo_code.partner != user:
            raise serializers.ValidationError(_("This promo code is not for you"))

        program = promo_code.program
        if not program:
            raise serializers.ValidationError(_("This promo code is not linked to a program"))

        if not program.active:
            raise serializers.ValidationError(_("The program for this promo code is inactive"))

        if program.date_from and program.date_to:
            if not (program.date_from <= today <= program.date_to):
                raise serializers.ValidationError(_("This promo code is not valid today"))
        else:
            raise serializers.ValidationError(_("This promo code is not valid today"))

        if promo_code.expiration_date and promo_code.expiration_date < today:
            raise serializers.ValidationError(_("This promo code has expired"))

        if hasattr(promo_code, "points") and promo_code.points <= 0:
            raise serializers.ValidationError(_("This promo code has no remaining uses"))
        return promo_code


class OrderDetailSerializer(serializers.ModelSerializer):
    order_items = serializers.SerializerMethodField()
    region = RegionSerializer(read_only=True)
    district = DistrictSerializer(read_only=True)
    branch = BranchSerializer(read_only=True)
    has_rated = serializers.SerializerMethodField()
    given_rating = serializers.SerializerMethodField()
    address_id = AddressReadSerializer(read_only=True)
    loyalty_card_data = serializers.SerializerMethodField()
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    source_display = serializers.CharField(source="get_source_display", read_only=True)
    payment_status_display = serializers.CharField(
        source="get_payment_status_display", read_only=True
    )
    payment_method_display = serializers.CharField(
        source="get_payment_method_display", read_only=True
    )
    type_display = serializers.CharField(source="get_type_display", read_only=True)
    cashback_amount = serializers.SerializerMethodField()
    check_xml = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id",
            "odoo_id",
            "name",
            "user",
            "type",
            "status",
            "payment_status",
            "payment_method",
            "created_at",
            "price",
            "branch",
            "region",
            "district",
            "given_rating",
            "address_id",
            "description",
            "promocode",
            "order_items",
            "completed_at",
            "cancelled_at",
            "updated_at",
            "has_rated",
            "loyalty_card_data",
            "total_price",
            "discount_amount",
            "status_display",
            "payment_status_display",
            "payment_method_display",
            "type_display",
            "source_display",
            "balance_status_name",
            "cashback_amount",
            "balance_amount",
            "fiscal_url",
            "promocode_amount",
            "source",
            "check_xml",
        ]
        read_only_fields = fields

    def get_name(self, obj):
        if obj.name == "No order name":
            return _("No order name")
        return obj.name

    def get_order_items(self, obj):
        items = obj.items.filter(product__product_type="PRODUCT")
        serializer = OrderItemSerializer(items, many=True, context=self.context)
        return serializer.data

    @extend_schema_field(LoyaltyCardDataSerializer)
    def get_loyalty_card_data(self, obj):
        cashback = Cashback.objects.filter(order=obj, amount__gt=0).first()
        if cashback:
            from app.models.card import Balance
            blance = Balance.objects.filter(user=obj.user).first()
            loyalty = blance.balance_status.name if blance else None
            payload = {
                "loyalty": loyalty,
                "percentage": cashback.percentage if cashback else None,
                "amount": cashback.amount if cashback else None,
                "used_amount": obj.balance_amount,
            }
            return payload
        return None

    def get_cashback_amount(self, obj):
        cashback = Cashback.objects.filter(order=obj, amount__gt=0).first()
        return cashback.cashback if cashback else Decimal("0.0")

    def get_has_rated(self, obj):
        request = self.context.get("request")
        return OrderRating.objects.filter(reviewer=request.user, order=obj).exists()

    def get_given_rating(self, obj):
        request = self.context.get("request")
        rating = OrderRating.objects.filter(reviewer=request.user, order=obj).first()
        return (
            OrderRatingSerializer(rating, context={"request": request}).data
            if rating
            else None
        )
    
    def get_check_xml(self, obj):
        from ..models.card import CheckForUser
        from ..utils.xml_generator import CheckXMLGenerator

        check = CheckForUser.objects.filter(order=obj).first()
        if not check or obj.payment_status != "COMPLETED":
            return None

        generator = CheckXMLGenerator()
        context_data = generator._prepare_context_data(check, obj.branch, request=self.context.get("request"))

        # Format products into a clean list
        products = []
        for item in obj.items.filter(product__product_type__in=("PRODUCT", "DELIVERY_PRICE")):
            mxic = item.product.mxik if item.product else None
            if not mxic:
                mxic = item.product.product_template.category.mxik if item.product and item.product.product_template and item.product.product_template.category else None
            products.append({
                "product": item.product.name if item.product else "",
                "quantity": item.quantity,
                "mxic": mxic,
                "price": f"{item.price:.2f}",
                "total": f"{item.total_price:.2f}"
            })

        # Get car number if order has a car
        car_number = obj.car.number if obj.car else None

        return {
            "company_name": context_data["company_name"],
            "company_city": context_data["company_city"],
            "company_street": context_data["company_street"],
            "company_phone": context_data["company_phone"],
            "company_logo": context_data["company_logo"],

            "cashier_name": context_data["cashier_name"],
            "order_number": context_data["order_number"],
            "order_id": obj.id,
            "customer_name": context_data["customer_name"],
            "order_date": context_data["order_date"],
            "car_number": car_number,

            "products": products,
            "source":context_data["source"],
            "vat":context_data["vat"],
            "current_balance": context_data["current_balance"],
            "cashback_used": context_data["cashback_used"],
            "cashback_added": context_data["cashback_added"],
            "cashback_percentage": context_data["cashback_percentage"],
            "cashback_status_name": context_data["cashback_status_name"],

            "total_amount": context_data["total_amount"],
            "card_amount": context_data["card_amount"],
            "cash_amount":context_data["cash_amount"],
            "payment_method": context_data["payment_method"],
            "currency": context_data["currency"],

            "fm_num": context_data["fm_num"],
            "f_num": context_data["f_num"],
            "qr_url": context_data["qr_url"]
        }

class PromoCodeValidationSerializer(serializers.Serializer):
    code = serializers.CharField()
    promo = None

    def validate_code(self, value):
        user = self.context["request"].user
        today = timezone.now().date()

        promo_code = PromoCode.objects.filter(
            code=value.strip(),
            active=True,
        ).select_related("program").first()

        if not promo_code:
            raise serializers.ValidationError(_("Invalid promo code"))

        if promo_code.partner and promo_code.partner != user:
            raise serializers.ValidationError(_("This promo code is not for you"))

        program = promo_code.program
        if not program:
            raise serializers.ValidationError(_("This promo code is not linked to a program"))

        if not program.active:
            raise serializers.ValidationError(_("The program for this promo code is inactive"))

        if program.date_from and program.date_to:
            if not (program.date_from <= today <= program.date_to):
                raise serializers.ValidationError(_("This promo code is not valid today"))

        if promo_code.expiration_date and promo_code.expiration_date < today:
            raise serializers.ValidationError(_("This promo code has expired"))

        if hasattr(promo_code, "points") and promo_code.points <= 0:
            raise serializers.ValidationError(_("This promo code has no remaining uses"))
        self.promo = promo_code
        return promo_code


class RatingTypeSerilazier(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model = RatingType
        fields = ["id", "icon", "name", "status"]

    def get_name(self, obj):
        lang = get_language()
        if lang == "ru":
            return obj.name_ru
        elif lang == "en":
            return obj.name_en
        return obj.name_uz


class OrderRatingSerializer(serializers.ModelSerializer):
    options_ids = serializers.PrimaryKeyRelatedField(
        queryset=RatingType.objects.all(), many=True
    )
    reviewer = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = OrderRating
        fields = [
            "id",
            "reviewer",
            "order",
            "rating",
            "description",
            "options_ids",
            "created_at",
        ]
        read_only_fields = ["reviewer", "created_at"]

    def validate(self, data):
        request = self.context.get("request")
        order = data.get("order")
        rating = int(data.get("rating"))

        if order.status != "COMPLETED":
            raise ValidationError(_("You can only rate completed orders"))

        if order.user != request.user:
            raise ValidationError(_("You can only rate your own orders"))
        if rating < 1 or rating > 5:
            raise ValidationError(_("Rating over ranged it should be from 1 to 5 "))
        if OrderRating.objects.filter(reviewer=request.user, order=order).exists():
            raise ValidationError(_("You have already rated this order"))
        return data

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["options_ids"] = RatingTypeSerilazier(
            instance.options_ids.all(), many=True, context=self.context
        ).data
        return data

    def create(self, validated_data):
        validated_data["reviewer"] = self.context["request"].user
        return super().create(validated_data)


class PaymentDataSerializer(serializers.Serializer):
    store_id = serializers.CharField(required=True)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    invoice_id = serializers.CharField(required=True)
    invoice_uuid = serializers.UUIDField(required=True)
    payment_time = serializers.DateTimeField(required=True)
    billing_id = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )
    uuid = serializers.UUIDField(required=True)
    sign = serializers.CharField(required=True)


class OrderPaymentSerializer(serializers.Serializer):
    order_id = serializers.IntegerField()
    payment_method = serializers.ChoiceField(
        choices=[
            "CLICK",
            "ON_RECEIVE",
            "XAZNA",
            "ALIF",
            "BEEPUL",
            "ANORBANK",
            "OSON",
            "PAYME",
            "CARD",
            "CASH",
            "UZUM",
        ]
    )

class LoyaltyProgramSerializer(serializers.ModelSerializer):
    branch = BranchOutputSerializer(read_only=True)
    class Meta:
        model = LoyaltyProgram
        fields = ["id", "name", "branch", "currency", "active", "date_from", "date_to"]


class PromoRewardSerializer(serializers.ModelSerializer):
    program = LoyaltyProgramSerializer(read_only=True)
    class Meta:
        model = PromoReward
        fields = [
            "id", "reward_type", "discount", "discount_applicability",
            "is_new_coming_reward","number_of_people_case",
            "program", "discount_line_product", "discount_max_amount",
            "discount_product_ids", "discount_product_category_id",
            "description", "active"]


class PromoCodeSerializer(serializers.ModelSerializer):
    program = LoyaltyProgramSerializer(read_only=True)
    reward = PromoRewardSerializer(read_only=True)
    class Meta:
        model = PromoCode
        fields = ["id", "code", "expiration_date", "active", "program", "reward", "partner",]

class DeliveryPriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryPrice
        fields = ["id", "district", "price"]
        read_only_fields = ["id"]


class BasketBulkDeleteSerializer(serializers.Serializer):
    product_ids = serializers.ListField(
        child=serializers.IntegerField(), required=True
    )