from django.utils.translation import get_language
from rest_framework import serializers
from app.models import OrderRating
from app.models.card import Card, CardImages, Balance, BalanceStatus, Cashback, BalanceUsageLimit
from app.serializers.order import OrderRatingSerializer, AddressReadSerializer


class CardImagesSerializer(serializers.ModelSerializer):
    class Meta:
        model = CardImages
        fields = ["id", "image"]
        read_only_fields = ["id", "image"]


class CardSerializer(serializers.ModelSerializer):
    background_image = serializers.PrimaryKeyRelatedField(
        queryset=CardImages.objects.all(), write_only=True, required=False
    )
    background_image_url = serializers.ImageField(
        source="background_image.image", read_only=True
    )

    class Meta:
        model = Card
        fields = [
            "id",
            "owner",
            "card_name",
            "card_number",
            "phone_number",
            "processing",
            "background_image",
            "background_image_url",
            "is_main",
            "is_active",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "owner",
            "card_name",
            "card_number",
            "phone_number",
            "processing",
            "background_image_url",
            "is_active",
            "created_at",
        ]


class CardBindSerializer(serializers.Serializer):
    pinfl = serializers.CharField(max_length=14, required=False, allow_blank=True)
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)


class BalanceStatusSerializer(serializers.ModelSerializer):
    description = serializers.SerializerMethodField()

    class Meta:
        model = BalanceStatus
        fields = [
            "id",
            "name",
            "percentage",
            "minimum_amount",
            "next_minimum_amount",
            "icon",
            "num",
            "time_line",
            "description",
            "created_at",
            "updated_at",
        ]

    def get_description(self, obj):
        lang = get_language()
        if lang == "uz":
            return obj.description_uz
        elif lang == "ru":
            return obj.description_ru
        return obj.description_en


class BalanceSerializer(serializers.ModelSerializer):
    balance_status = BalanceStatusSerializer()
    min_amount = serializers.SerializerMethodField()
    max_amount = serializers.SerializerMethodField()

    class Meta:
        model = Balance
        fields = [
            "id",
            "user",
            "unique_id",
            "balance",
            "total_sales",
            "balance_status",
            "min_amount",
            "max_amount",
            "created_at",
            "updated_at",
        ]

    def get_min_amount(self, obj):
        usage_limit = BalanceUsageLimit.objects.order_by('-created_at').first()
        return usage_limit.min_amount if usage_limit else 0.0

    def get_max_amount(self, obj):
        usage_limit = BalanceUsageLimit.objects.order_by('-created_at').first()
        return usage_limit.max_amount if usage_limit else 0.0


class CashbackSerializer(serializers.ModelSerializer):
    balance = BalanceSerializer(read_only=True)
    has_rated_related_order = serializers.SerializerMethodField()
    branch = serializers.SerializerMethodField(read_only=True)
    address = serializers.SerializerMethodField(read_only=True)
    given_rating = serializers.SerializerMethodField(read_only=True)
    check_xml = serializers.SerializerMethodField()
    
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        # Ensure amount is positive
        if 'amount' in representation and representation['amount'] is not None:
            representation['amount'] = abs(float(representation['amount']))
        # Ensure cashback is positive
        if 'cashback' in representation and representation['cashback'] is not None:
            representation['cashback'] = abs(float(representation['cashback']))
        return representation

    def get_given_rating(self, obj):
        rating = OrderRating.objects.filter(order=obj.order).first()
        return (
            OrderRatingSerializer(
                rating, context={"request": self.context.get("request")}
            ).data
            if rating
            else None
        )
    def get_check_xml(self, obj):
        from ..models.card import CheckForUser
        from ..utils.xml_generator import CheckXMLGenerator

        if not obj.order:
            return None

        check = CheckForUser.objects.filter(order=obj.order).first()
        if not check or obj.order.payment_status != "COMPLETED":
            return None

        generator = CheckXMLGenerator()
        context_data = generator._prepare_context_data(check, obj.order.branch, request=self.context.get("request"))

        # Format products into a clean list
        products = []
        for item in obj.order.items.filter(product__product_type="PRODUCT"):
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

        return {
            "company_name": context_data["company_name"],
            "company_city": context_data["company_city"],
            "company_street": context_data["company_street"],
            "company_phone": context_data["company_phone"],
            "company_logo": context_data["company_logo"],

            "cashier_name": context_data["cashier_name"],
            "order_number": context_data["order_number"],
            "order_id": obj.order.id,
            "customer_name": context_data["customer_name"],
            "order_date": context_data["order_date"],

            "products": products,
            "source": context_data["source"],
            "vat": context_data["vat"],
            "current_balance": context_data["current_balance"],
            "cashback_used": context_data["cashback_used"],
            "cashback_added": context_data["cashback_added"],
            "cashback_percentage": context_data["cashback_percentage"],
            "cashback_status_name": context_data["cashback_status_name"],

            "total_amount": context_data["total_amount"],
            "card_amount": context_data["card_amount"],
            "cash_amount": context_data["cash_amount"],
            "payment_method": context_data["payment_method"],
            "currency": context_data["currency"],

            "fm_num": context_data["fm_num"],
            "f_num": context_data["f_num"],
            "qr_url": context_data["qr_url"]
        }
    def get_address(self, obj):
        if obj.order and obj.order.address_id:
            address = obj.order.address_id
            return {
                "region": address.region.name if address.region else None,
                "district": address.district.name if address.district else None,
                "address": address.additional,
            }
        return None

    def get_branch(self, obj):
        return obj.order.branch.name if obj.order and obj.order.branch else None

    def get_has_rated_related_order(self, obj):
        return OrderRating.objects.filter(order=obj.order).exists()

    class Meta:
        model = Cashback
        fields = [
            "id",
            "order",
            "balance",
            "amount",
            "state",
            "percentage",
            "cashback",
            "created_at",
            "updated_at",
            "has_rated_related_order",
            "branch",
            "address",
            "given_rating",
            "check_xml",
        ]
