from app.models.product import (
    ProductTemplate,
    Option,
    ProductOption,
    WareHouse,
    Location,
    StockQuant,
    Product,
    Variant,
    ProductVariants,
    Category,
    Branch,
    Brand,
    Pricelist,
    Discount,
    Currency,
    OilBrand,
    FilterBrand,
    ProductTemplateImage,
    Offer,
    Partner,
)
from rest_framework import serializers
from odoo.serializers.custom_base_serializer import (
    BaseOdooIDSerializer,
    Base64ImageField,
)


class BrandSerializer(BaseOdooIDSerializer):
    image = Base64ImageField(required=False, allow_null=True)

    class Meta:
        model = Brand
        fields = [
            "id",
            "odoo_id",
            "sync_status",
            "name_uz",
            "name_ru",
            "name_en",
            "image",
            "send_odoo",
            "is_top",
        ]


class VariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Variant
        fields = ["id", "odoo_id", "sync_status", "name", "send_odoo"]


class OptionSerializer(BaseOdooIDSerializer):
    variant = serializers.SlugRelatedField(
        queryset=Variant.objects.all(), slug_field="odoo_id"
    )

    class Meta:
        model = Option
        fields = ["id", "sync_status", "odoo_id", "variant", "name", "send_odoo"]


class LocationSerializer(BaseOdooIDSerializer):
    parent_location = serializers.SlugRelatedField(
        queryset=Location.objects.all(),
        slug_field="odoo_id",
        allow_null=True,
        required=False,
    )
    branch = serializers.SlugRelatedField(
        queryset=Branch.objects.all(),
        slug_field="odoo_id",
        allow_null=True,
        required=False,
    )
    warehouse = serializers.SlugRelatedField(
        queryset=WareHouse.objects.all(),
        slug_field="odoo_id",
        allow_null=True,
        required=False,
    )

    class Meta:
        model = Location
        fields = "__all__"


class ProductOptionSerializer(BaseOdooIDSerializer):
    option = serializers.SlugRelatedField(
        queryset=Option.objects.all(), slug_field="odoo_id"
    )
    product_template = serializers.SlugRelatedField(
        queryset=ProductTemplate.objects.all(), slug_field="odoo_id"
    )
    product_template_attribute_line = serializers.SlugRelatedField(
        queryset=ProductVariants.objects.all(), slug_field="odoo_id"
    )

    class Meta:
        model = ProductOption
        fields = [
            "id",
            "product_template_attribute_line",
            "product_template",
            "odoo_id",
            "sync_status",
            "option",
            "additional_price",
            "send_odoo",
        ]


class CategorySerializer(BaseOdooIDSerializer):
    parent = serializers.SlugRelatedField(
        queryset=Category.objects.all(),
        slug_field="odoo_id",
        allow_null=True,
        required=False,
    )
    image = Base64ImageField(required=False, allow_null=True)


    def validate_parent(self, parent):
        if parent and parent.depth >= 1:
            raise serializers.ValidationError(
                "Category depth must be 2 levels or less"
            )
        if parent and parent.product_templates.exists():
            raise serializers.ValidationError(
                "Cannot add a subcategory to a category that already has products."
            )
        return parent

    class Meta:
        model = Category
        fields = "__all__"

class ProductTemplateImageSerializer(BaseOdooIDSerializer):
    product_template = serializers.SlugRelatedField(
        queryset=ProductTemplate.objects.all(),
        slug_field='odoo_id'
    )
    image = Base64ImageField(required=False, allow_null=True)
    class Meta:
        model = ProductTemplateImage
        fields = "__all__"

class ProductTemplateSerializer(BaseOdooIDSerializer):
    category = serializers.SlugRelatedField(
        queryset=Category.objects.all(), slug_field="odoo_id"
    )
    brand = serializers.SlugRelatedField(
        queryset=Brand.objects.all(),
        slug_field="odoo_id",
        allow_null=True,
        required=False,
    )
    branch = serializers.SlugRelatedField(
        queryset=Branch.objects.all(),
        slug_field="odoo_id",
        allow_null=True,
        required=False,
    )
    image = Base64ImageField(required=False, allow_null=True)

    class Meta:
        model = ProductTemplate
        fields = [
            "id",
            "odoo_id",
            "sync_status",
            "product_type",
            "name",
            "description",
            "image",
            "category",
            "brand",
            "price",
            "send_odoo",
            "branch",
            "is_visible",
            "is_top",
        ]

    def validate(self, data):
        category = data.get("category")
        if category and category.category_set.exists():
            raise serializers.ValidationError(
                "Product can only be assigned to a leaf category (one that has no subcategories)."
            )
        return data


class ProductVariantsSerializer(BaseOdooIDSerializer):
    product_template = serializers.SlugRelatedField(
        queryset=ProductTemplate.objects.all(), slug_field="odoo_id"
    )
    product_options = serializers.SlugRelatedField(
        queryset=Option.objects.all(), slug_field="odoo_id", many=True
    )
    variant = serializers.SlugRelatedField(
        queryset=Variant.objects.all(), slug_field="odoo_id"
    )

    class Meta:
        model = ProductVariants
        fields = [
            "id",
            "odoo_id",
            "sync_status",
            "variant",
            "product_template",
            "product_options",
            "send_odoo",
        ]


class ProductVariantGerSerialzier(serializers.ModelSerializer):
    variant = VariantSerializer()
    product_template = ProductTemplateSerializer()
    product_options = ProductOptionSerializer(many=True)

    class Meta:
        model = ProductVariants
        fields = "__all__"


class ProductSerializer(BaseOdooIDSerializer):
    product_template = serializers.SlugRelatedField(
        queryset=ProductTemplate.objects.all(), slug_field="odoo_id"
    )
    attributes = serializers.SlugRelatedField(
        queryset=Option.objects.all(), slug_field="odoo_id", many=True
    )
    image = Base64ImageField(required=False, allow_null=True)

    class Meta:
        model = Product
        fields = "__all__"


class WareHouseSerializer(BaseOdooIDSerializer):
    branch = serializers.SlugRelatedField(
        queryset=Branch.objects.all(),
        slug_field="odoo_id",
        required=False,
        allow_null=True,
    )
    class Meta:
        model = WareHouse
        fields = "__all__"


class StockQuantSerializer(BaseOdooIDSerializer):
    product = serializers.SlugRelatedField(
        queryset=Product.objects.all(), slug_field="odoo_id"
    )
    location = serializers.SlugRelatedField(
        queryset=Location.objects.all(), slug_field="odoo_id"
    )
    branch = serializers.CharField(required=False)

    class Meta:
        model = StockQuant
        fields = "__all__"

    def validate(self, data):
        location = data.get("location")
        if not location:
            raise serializers.ValidationError("Location is required.")
        if not location.branch:
            raise serializers.ValidationError(
                "Selected location must have an associated branch."
            )
        return data

    def create(self, validated_data):
        validated_data["branch"] = validated_data["location"].branch
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data["branch"] = validated_data["location"].branch
        return super().update(instance, validated_data)


class CurrencySerializer(BaseOdooIDSerializer):
    class Meta:
        model = Currency
        fields = "__all__"


class PricelistSerializer(BaseOdooIDSerializer):
    branch = serializers.SlugRelatedField(
        queryset=Branch.objects.all(),
        slug_field="odoo_id",
        required=False,
        allow_null=True,
    )
    currency = serializers.SlugRelatedField(
        queryset=Currency.objects.all(), slug_field="odoo_id"
    )

    class Meta:
        model = Pricelist
        fields = "__all__"


class DiscountSerializer(BaseOdooIDSerializer):
    branch = serializers.SlugRelatedField(
        queryset=Branch.objects.all(),
        slug_field="odoo_id",
        required=False,
        allow_null=True,
    )
    product = serializers.SlugRelatedField(
        queryset=Product.objects.all(),
        slug_field="odoo_id",
        required=False,
        allow_null=True,
    )
    product_template = serializers.SlugRelatedField(
        queryset=ProductTemplate.objects.all(),
        slug_field="odoo_id",
        required=False,
        allow_null=True,
    )
    pricelist = serializers.SlugRelatedField(
        queryset=Pricelist.objects.all(),
        slug_field="odoo_id",
        required=False,
        allow_null=True,
    )
    category = serializers.SlugRelatedField(
        queryset=Category.objects.all(),
        slug_field="odoo_id",
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Discount
        fields = "__all__"


class OilBrandSerializer(BaseOdooIDSerializer):
    class Meta:
        model = OilBrand
        fields = ["id", "odoo_id", "sync_status", "name", "send_odoo"]


class FilterBrandSerializer(BaseOdooIDSerializer):
    class Meta:
        model = FilterBrand
        fields = ["id", "odoo_id", "sync_status", "name", "send_odoo"]


class OfferSerializer(BaseOdooIDSerializer):
    image = Base64ImageField()  # required by model

    class Meta:
        model = Offer
        fields = "__all__"

    def validate(self, attrs):
        # merge instance for partial updates
        data = {**({} if not self.instance else {
            "title_uz": self.instance.title_uz,
            "title_en": self.instance.title_en,
            "title_ru": self.instance.title_ru,
            "start_date": self.instance.start_date,
            "end_date": self.instance.end_date,
        }), **attrs}

        if not any([data.get("title_uz"), data.get("title_en"), data.get("title_ru")]):
            raise serializers.ValidationError(
                {"title_uz": "At least one title (uz, en, ru) must be provided."}
            )

        start_date = data.get("start_date")
        end_date = data.get("end_date")
        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError(
                {"end_date": "The end date must be later than or equal to the start date."}
            )
        return attrs
    

class PartnerSerializer(BaseOdooIDSerializer):
    picture = Base64ImageField(required=False, allow_null=True)

    class Meta:
        model = Partner
        fields = "__all__"

    def validate(self, attrs):
        return attrs