from app.models import Order
from app.models.product import (
    SavedProduct,
    Product,
    Discount,
    Category,
    ProductOption,
    ProductTemplate,
    Brand,
    Offer,
    Option,
    Variant,
    ProductRating,
    OilBrand,
    FilterBrand,
    StockQuant,
    ProductTemplateImage,
    User,
    Partner,
)
from django.utils.translation import gettext_lazy as _, get_language
import base64
from django.core.files.base import ContentFile
from rest_framework import serializers
from django.utils.timezone import now
from decimal import Decimal
from rest_framework.exceptions import ValidationError
from django.db.models import F, Q
from django.db.models import Avg
from app.serializers.company_info import BranchOutputSerializer


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        # Handle base64 string
        if isinstance(data, str) and data.startswith("data:image"):
            try:
                # Extract the format and encoded data
                format, imgstr = data.split(";base64,")
                ext = format.split("/")[-1]  # Get file extension

                # Decode the base64 data
                decoded_file = ContentFile(base64.b64decode(imgstr), name=f"temp.{ext}")
                return decoded_file
            except (ValueError, TypeError, AttributeError):
                raise serializers.ValidationError("Invalid base64 image data")

        # Handle regular file upload
        return super().to_internal_value(data)


class DiscountedProductSerializer(serializers.ModelSerializer):

    class Meta:
        model = Product
        fields = ["id", "odoo_id", "product_template"]


class DiscountSerializer(serializers.ModelSerializer):
    product = DiscountedProductSerializer(Product.objects.all())

    class Meta:
        model = Discount
        fields = [
            "id",
            "odoo_id",
            "product",
            "user",
            "amount",
            "percent",
            "time_from",
            "time_to",
            "quantity",
        ]

    def validate_quantity(self):
        quantity = self.validated_data.get("quantity", None)

        if quantity is not None and quantity < 1:
            raise serializers.ValidationError("Quantiy must be positive number")
        return quantity


class CategoryOutputSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    has_sub_category = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ["id", "odoo_id", "has_sub_category", "name", "image"]

    def get_name(self, obj):
        lang = get_language()
        if lang == "ru":
            return obj.name_ru
        elif lang == "en":
            return obj.name_en
        return obj.name_uz
    def get_has_sub_category(self,obj):
        return Category.objects.filter(parent=obj).exists()


class CategoryInputSerializer(serializers.ModelSerializer):
    parent = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = Category
        fields = ["id", "odoo_id", "name_uz", "name_ru", "name_en", "image", "parent", "is_visible"]
        read_only_fields = ["id"]

    def validate_parent(self, parent):
        if parent and parent.depth >= 1:
            raise serializers.ValidationError(
                _("Category depth must be 2 levels or less")
            )
        if parent and parent.product_templates.exists():
            raise serializers.ValidationError(
                _("Cannot add a subcategory to a category that already has products.")
            )
        return parent

    def create(self, validated_data):
        instance = super().create(validated_data)
        instance.full_clean()
        return instance

    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        instance.full_clean()
        return instance


class BrandOutputSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model = Brand
        fields = [
            "id",
            "name",
            "name_uz",
            "name_ru",
            "name_en",
            "image",
            "created_at",
            "updated_at",
            "is_top",
        ]

    def get_name(self, obj):
        lang = get_language()
        if lang == "ru":
            return obj.name_ru
        elif lang == "en":
            return obj.name_en
        return obj.name_uz


class BrandInputSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ["id", "name_uz", "name_ru", "name_en", "image", "is_top"]
        read_only_fields = ["id"]


class ProductTemplateImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductTemplateImage
        fields = ["id", "image"]


class ProductOptionSerializer(serializers.ModelSerializer):

    class Meta:
        model = ProductOption
        fields = ["id", "additional_price", "option"]


class ProductTempleteSerializer(serializers.ModelSerializer):
    category = CategoryOutputSerializer()
    brand_detail = BrandOutputSerializer(source="brand")
    images = ProductTemplateImageSerializer(many=True, read_only=True)

    class Meta:
        model = ProductTemplate
        fields = [
            "id",
            "odoo_id",
            "name",
            "images",
            "price",
            "url",
            "on_hand",
            "description",
            "category",
            "brand_detail",
            "branch",
            "created_at",
            "updated_at",
        ]


class VariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Variant
        fields = ["id", "name"]


class OptionSerializer(serializers.ModelSerializer):
    variant = VariantSerializer()

    class Meta:
        model = Option
        fields = ["id", "name", "variant"]


class OptionGetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Option
        fields = ["id", "name"]


class VariantoptionsSerializer(serializers.ModelSerializer):
    variant_option = OptionGetSerializer(many=True, read_only=True)

    class Meta:
        model = Variant
        fields = ["id", "name", "variant_option"]


class ProductRatingSerializer(serializers.ModelSerializer):
    reviewer_name = serializers.SerializerMethodField(read_only=True)
    reviewer = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = ProductRating
        fields = [
            "id",
            "reviewer",
            "reviewer_name",
            "anonymous",
            "product",
            "rating",
            "description",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def validate(self, data):
        user = self.context["request"].user
        product = data.get("product")
        rating = int(data.get("rating"))

        has_completed_order = Order.objects.filter(
            user=user, status="COMPLETED", items__product=product
        ).exists()

        if not has_completed_order:
            raise serializers.ValidationError(
                "You can only review products you have completed orders for."
            )

        if rating < 1 or rating > 5:
            raise ValidationError("Rating over ranged it should be from 1 to 5 ")
        return data

    def get_reviewer_name(self, obj):
        if obj.anonymous:
            # Get the current language
            from django.utils.translation import get_language

            current_language = get_language()
            translations = {
                'en': "Anonymous",
                'uz': "Anonim",
                'ru': "Аноним",
            }
            return translations.get(current_language, translations['en'])
        return obj.reviewer.info.first_name if obj.reviewer.has_info else "No Name"

    def create(self, validated_data):
        validated_data["reviewer"] = self.context["request"].user
        return super().create(validated_data)


class ProductSerializer(serializers.ModelSerializer):
    product_options = ProductOptionSerializer(many=True, read_only=True)
    product_template = ProductTempleteSerializer(read_only=True)
    price = serializers.SerializerMethodField()
    attributes = serializers.SerializerMethodField()
    have_discount = serializers.SerializerMethodField(read_only=True)
    price_in_discount = serializers.SerializerMethodField(read_only=True)
    ratings = ProductRatingSerializer(many=True, read_only=True)
    available_branches = serializers.SerializerMethodField(read_only=True)
    url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "odoo_id",
            "product_template",
            "description",
            "image",
            "free_quantity",
            "price",
            "created_at",
            "attributes",
            "ratings",
            "have_discount",
            "price_in_discount",
            "updated_at",
            "product_options",
            "is_top",
            "available_branches",
            "url",
        ]

    def get_available_branches(self, obj):
        from app.models.company_info import Branch

        branches = Branch.objects.filter(
            stock_quants_branch__product=obj, stock_quants_branch__quantity__gt=0
        ).distinct()
        return BranchOutputSerializer(branches, many=True, context=self.context).data

    def validate_price(self, value):
        if value < 0:
            raise serializers.ValidationError(
                _("Price must be greater than or equal to 0.")
            )
        return value

    def get_have_discount(self, obj):
        return self._get_valid_discount(obj) is not None

    def get_price_in_discount(self, obj):
        discount_amount = self.get_discount_amount(obj)
        if discount_amount:
            return round(obj.price - discount_amount, 2)
        return obj.price

    def get_discount_amount(self, obj):
        discount = self._get_valid_discount(obj)
        if not discount:
            return None

        if discount.discount_type == "percentage":
            return round(obj.price * Decimal(discount.percent) / 100, 2)
        elif discount.discount_type == "fixed":
            return min(
                discount.amount, obj.price
            )  # Ensure it doesn't exceed product price
        return None

    def _get_valid_discount(self, product):
        now_time = now()

        discount_qs = Discount.objects.filter(
            Q(pricelist__active=True) &
            Q(pricelist__branch__is_main=True) &
            (Q(time_from__lte=now_time) | Q(time_from__isnull=True)) &
            (Q(time_to__gte=now_time) | Q(time_to__isnull=True))
        ).order_by("-amount", "-percent")

        discount = discount_qs.filter(product=product, product__isnull=False).first()
        if discount:
            return discount

        if product.product_template:
            discount = discount_qs.filter(
                product_template=product.product_template,
                product_template__isnull=False,
                product__isnull=True
            ).first()
            if discount:
                return discount

        if product.product_template and product.product_template.category:
            discount = discount_qs.filter(
                category=product.product_template.category,
                category__isnull=False,
                product__isnull=True,
                product_template__isnull=True
            ).first()
            if discount:
                return discount

        if product.product_template and product.product_template.branch:
            discount = discount_qs.filter(
                branch=product.product_template.branch,
                branch__isnull=False,
                product__isnull=True,
                product_template__isnull=True,
                category__isnull=True
            ).first()
            if discount:
                return discount

        return None

    def get_price(self, obj):
        return obj.price

    def get_attributes(self, obj):
        return [
            {
                "id": option.variant.id,
                "name": option.variant.name,
                "variant": {"id": option.id, "name": option.name},
            }
            for option in obj.attributes.select_related("variant").all()
        ]

    def get_url(self, obj):
        return obj.product_template.url if obj.product_template else None


class ProductOptionForTemplateSerializer(serializers.ModelSerializer):
    """Serializer to show additional_price for each option in product template"""

    class Meta:
        model = ProductOption
        fields = ["additional_price"]


class ProductVariantOptionSerializer(serializers.ModelSerializer):
    """Serializer for options within a variant with additional_price and availability"""

    product_option = serializers.SerializerMethodField()
    available = serializers.SerializerMethodField()

    class Meta:
        model = Option
        fields = ["id", "odoo_id", "name", "product_option", "available"]

    def get_product_option(self, obj):
        # Get the product template from context
        product_template = self.context.get("product_template")
        if not product_template:
            return None

        product_option = ProductOption.objects.filter(
            product_template=product_template, option=obj
        ).first()

        if product_option:
            return ProductOptionForTemplateSerializer(product_option).data
        return None

    def get_available(self, obj):
        product_template = self.context.get("product_template")
        if not product_template:
            return False

        has_available_stock = Product.objects.filter(
            product_template=product_template,
            attributes__id=obj.id,  # Check if option is in attributes
            stock_quants__quantity__gt=F("stock_quants__reserved_quantity"),
        ).exists()

        return has_available_stock

    def to_representation(self, instance):
        """Override to filter out options with null product_option"""
        representation = super().to_representation(instance)

        # If product_option is None, we exclude this option from the representation
        if not representation.get("product_option"):
            return None

        # If 'name' or 'available' is null, we remove the option
        if (
            representation.get("name") is None
            or representation.get("available") is None
        ):
            return None

        return representation


class ProductVariantDetailSerializer(serializers.ModelSerializer):
    """Serializer for variants with their options and prices"""

    variant_option = ProductVariantOptionSerializer(many=True, read_only=True)

    class Meta:
        model = Variant
        fields = ["id", "odoo_id", "name", "variant_option"]

    def to_representation(self, instance):
        """Override to filter out variants with no valid options"""
        representation = super().to_representation(instance)

        # Remove null variant_options
        valid_variant_options = [
            option for option in representation.get("variant_option", []) if option
        ]

        # Update the variant_option field to remove null values
        representation["variant_option"] = valid_variant_options

        # If there are no valid options, exclude the variant entirely
        if not valid_variant_options:
            return None

        return representation


class ProductTemplateDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for ProductTemplate with variants, options, prices, images, and single product details"""

    variants = serializers.SerializerMethodField()
    category = CategoryOutputSerializer()
    brand = BrandOutputSerializer()
    recent_ratings = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    images = ProductTemplateImageSerializer(many=True, read_only=True)
    single_product = serializers.SerializerMethodField()

    class Meta:
        model = ProductTemplate
        fields = [
            "id",
            "odoo_id",
            "name",
            "images",
            "price",
            "url",
            "on_hand",
            "description",
            "single_product_id",
            "category",
            "brand",
            "created_at",
            "updated_at",
            "variants",
            "recent_ratings",
            "average_rating",
            "single_product",
            "is_top",
        ]

    def get_variants(self, obj):
        variants = (
            Variant.objects.filter(product_template_variants__product_template=obj)
            .distinct()
            .prefetch_related("variant_option")
        )

        # Serialize the variants with valid options
        serializer = ProductVariantDetailSerializer(
            variants, many=True, context={"product_template": obj}
        )
        return serializer.data

    def get_recent_ratings(self, obj):
        ratings = ProductRating.objects.filter(product__product_template=obj).order_by(
            "-created_at"
        )[:5]
        return ProductRatingSerializer(ratings, many=True).data

    def get_average_rating(self, obj):
        average_rating = ProductRating.objects.filter(
            product__product_template=obj
        ).aggregate(Avg("rating"))["rating__avg"]
        return average_rating or 0

    def get_single_product(self, obj):
        if obj.single_product_id:
            try:
                product = Product.objects.get(id=obj.single_product_id)
                return ProductGetSerializer(product, context=self.context).data
            except Product.DoesNotExist:
                return None
        return None


class ProductTemplateListSerializer(serializers.ModelSerializer):
    """Simplified serializer for listing ProductTemplates"""

    category = CategoryOutputSerializer()
    images = ProductTemplateImageSerializer(many=True, read_only=True)
    single_product = serializers.SerializerMethodField()

    class Meta:
        model = ProductTemplate
        fields = [
            "id",
            "name",
            "images",
            "price",
            "url",
            "single_product_id",
            "category",
            "created_at",
            "updated_at",
            "single_product",
            "is_top",
        ]

    def get_single_product(self, obj):
        if obj.single_product_id:
            try:
                product = Product.objects.get(id=obj.single_product_id)
                return ProductGetSerializer(product, context=self.context).data
            except Product.DoesNotExist:
                return None
        return None


class ProductGetSerializer(serializers.ModelSerializer):
    price = serializers.SerializerMethodField()
    have_discount = serializers.SerializerMethodField(read_only=True)
    price_in_discount = serializers.SerializerMethodField(read_only=True)
    ratings = ProductRatingSerializer(many=True, read_only=True)
    available_branches = serializers.SerializerMethodField(read_only=True)
    url = serializers.SerializerMethodField(read_only=True)
    attributes = serializers.SerializerMethodField(read_only=True) 

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "odoo_id",
            "description",
            "attributes",
            "image",
            "price",
            "created_at",
            "ratings",
            "have_discount",
            "price_in_discount",
            "updated_at",
            "is_top",
            "available_branches",
            "url",
        ]

    def get_available_branches(self, obj):
        from app.models.company_info import Branch

        branches = Branch.objects.filter(
            stock_quants_branch__product=obj, stock_quants_branch__quantity__gt=0
        ).distinct()
        return BranchOutputSerializer(branches, many=True, context=self.context).data

    def validate_price(self, value):
        if value < 0:
            raise serializers.ValidationError(
                _("Price must be greater than or equal to 0.")
            )
        return value

    def get_have_discount(self, obj):
        return self._get_valid_discount(obj) is not None

    def get_price_in_discount(self, obj):
        discount_amount = self.get_discount_amount(obj)
        if discount_amount:
            return round(obj.price - discount_amount, 2)
        return obj.price

    def get_discount_amount(self, obj):
        discount = self._get_valid_discount(obj)
        if not discount:
            return None

        if discount.discount_type == "percentage":
            return round(obj.price * Decimal(discount.percent) / 100, 2)
        elif discount.discount_type == "fixed":
            return min(
                discount.amount, obj.price
            )  # Ensure it doesn't exceed product price
        return None

    def _get_valid_discount(self, product):
        now_time = now()

        discount_qs = Discount.objects.filter(
            Q(pricelist__active=True) &
            Q(pricelist__branch__is_main=True) &
            (Q(time_from__lte=now_time) | Q(time_from__isnull=True)) &
            (Q(time_to__gte=now_time) | Q(time_to__isnull=True))
        ).order_by("-amount", "-percent")

        discount = discount_qs.filter(product=product, product__isnull=False).first()
        if discount:
            return discount

        if product.product_template:
            discount = discount_qs.filter(
                product_template=product.product_template,
                product_template__isnull=False,
                product__isnull=True
            ).first()
            if discount:
                return discount

        if product.product_template and product.product_template.category:
            discount = discount_qs.filter(
                category=product.product_template.category,
                category__isnull=False,
                product__isnull=True,
                product_template__isnull=True
            ).first()
            if discount:
                return discount

        if product.product_template and product.product_template.branch:
            discount = discount_qs.filter(
                branch=product.product_template.branch,
                branch__isnull=False,
                product__isnull=True,
                product_template__isnull=True,
                category__isnull=True
            ).first()
            if discount:
                return discount

        return None

    def get_price(self, obj):
        return obj.price

    def get_attributes(self, obj):
        return [
            {
                "id": option.variant.id,
                "name": option.variant.name,
                "variant": {"id": option.id, "name": option.name},
            }
            for option in obj.attributes.select_related("variant").all()
        ]

    def get_url(self, obj):
        return obj.product_template.url if obj.product_template else None


class ProductShortSerializer(serializers.ModelSerializer):
    has_rated = serializers.SerializerMethodField(read_only=True)
    given_rating = serializers.SerializerMethodField(read_only=True)
    attributes = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Product
        fields = ["id", "name", "is_top", "image", "price", "has_rated", "given_rating", "attributes"]

    def get_has_rated(self, obj):
        request = self.context.get("request")
        if (
            not request
            or not hasattr(request, "user")
            or not request.user.is_authenticated
        ):
            return False
        return ProductRating.objects.filter(reviewer=request.user, product=obj).exists()

    def get_given_rating(self, obj):

        request = self.context.get("request")
        if (
            not request
            or not hasattr(request, "user")
            or not request.user.is_authenticated
        ):
            return None
        rating = ProductRating.objects.filter(
            reviewer=request.user, product=obj
        ).first()
        return (
            ProductRatingSerializer(rating, context={"request": request}).data
            if rating
            else None
        )
    
    def get_attributes(self, obj):
        return [
            {
                "id": option.variant.id,
                "name": option.variant.name,
                "option": {"id": option.id, "name": option.name},
            }
            for option in obj.attributes.select_related("variant").all()
        ]


class OfferGetSerializer(serializers.ModelSerializer):
    description = serializers.SerializerMethodField()
    title = serializers.SerializerMethodField()

    class Meta:
        model = Offer
        fields = [
            "id",
            "title",
            "image",
            "start_date",
            "end_date",
            "description",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        start_date = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end_date = attrs.get("end_date", getattr(self.instance, "end_date", None))
        if start_date and end_date and start_date >= end_date:
            raise serializers.ValidationError(
                "The end date must be later than the start date"
            )
        return attrs

    def get_language_field(self, instance, field_name):
        language = get_language()
        if language not in ["uz", "en", "ru"]:
            language = "en"
        field = f"{field_name}_{language}"
        return getattr(instance, field, None)

    def get_title(self, instance):
        return self.get_language_field(instance, "title")

    def get_description(self, instance):
        return self.get_language_field(instance, "description")


class OfferCreateSerializer(serializers.ModelSerializer):
    title_uz = serializers.CharField(required=False, allow_blank=True)
    title_en = serializers.CharField(required=False, allow_blank=True)
    title_ru = serializers.CharField(required=False, allow_blank=True)
    description_uz = serializers.CharField(required=False, allow_blank=True)
    description_en = serializers.CharField(required=False, allow_blank=True)
    description_ru = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Offer
        fields = [
            "odoo_id",
            "title_uz",
            "title_en",
            "title_ru",
            "description_uz",
            "description_en",
            "description_ru",
            "image",
            "start_date",
            "end_date",
        ]

    def validate(self, attrs):
        if not any(
            [attrs.get("title_uz"), attrs.get("title_en"), attrs.get("title_ru")]
        ):
            raise serializers.ValidationError(
                "At least one title (uz, en, ru) must be provided."
            )

        start_date = attrs.get("start_date")
        end_date = attrs.get("end_date")
        if start_date and end_date and start_date >= end_date:
            raise serializers.ValidationError(
                "The end date must be later than the start date."
            )

        return attrs


class SavedProductSerializer(serializers.ModelSerializer):
    product_template = ProductTemplateDetailSerializer()

    class Meta:
        model = SavedProduct
        fields = ["id", "odoo_id", "user", "product_template", "saved_at"]
        read_only_fields = ["saved_at", "user"]


class OilBrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = OilBrand
        fields = [
            "id",
            "name",
        ]


class FilterBrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = FilterBrand
        fields = ["id", "name"]


class ProductSearchSerializer(serializers.ModelSerializer):
    images = ProductTemplateImageSerializer(many=True, read_only=True)

    class Meta:
        model = ProductTemplate
        fields = ["id", "name", "price", "images"]


class CategorySearchSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ["id", "name"]

    def get_name(self, obj):
        lang = get_language()
        if lang == "ru":
            return obj.name_ru
        elif lang == "en":
            return obj.name_en
        return obj.name_uz

class PartnerSerializer(serializers.ModelSerializer):

    class Meta:
        model = Partner
        fields = "__all__"
        
class PartnerGetSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model = Partner
        fields = [
            "id",
            "name",
            "picture",
        ]
    
    def get_name(self, obj):
        lang = get_language()
        if lang == "ru":
            return obj.name_ru
        elif lang == "en":
            return obj.name_en
        return obj.name_uz
