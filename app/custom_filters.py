from django_filters import rest_framework as filters
from django.db.models import Q
from app.models import Order, Car, Branch
from app.models.product import (
    Category,
    Product,
    ProductTemplate,
    Brand,
    Option,
    Variant,
    ProductRating,
)
from django.db.models.functions import ExtractMonth, ExtractYear
from django.contrib.postgres.search import TrigramSimilarity
from app.models.card import Cashback
from django.db.models import Q
from django.utils.translation import gettext_lazy as _


class ProductFilter(filters.FilterSet):
    category = filters.ModelChoiceFilter(
        field_name="product_template__category",
        queryset=Category.objects.all(),
        label="Category",
    )
    product_template = filters.ModelChoiceFilter(
        field_name="product_template",
        queryset=ProductTemplate.objects.all(),
        label="Product Template",
    )
    attributes = filters.ModelMultipleChoiceFilter(
        field_name="attributes",
        queryset=Option.objects.all(),
        label="Attributes",
    )

    brand = filters.ModelChoiceFilter(
        field_name="product_template__brand",
        queryset=Brand.objects.all(),
        label="Brand",
    )
    min_price = filters.NumberFilter(field_name="price", lookup_expr="gte")
    max_price = filters.NumberFilter(field_name="price", lookup_expr="lte")
    odoo_id = filters.CharFilter(field_name="odoo_id", lookup_expr="exact")
    is_top = filters.BooleanFilter(field_name="is_top", label="Top Product")

    has_odoo_id = filters.BooleanFilter(
        method="filter_has_odoo_id", label="Has Odoo ID"
    )

    def filter_has_odoo_id(self, queryset, name, value):
        if value:
            return queryset.exclude(odoo_id__isnull=True).exclude(odoo_id="")
        return queryset.filter(Q(odoo_id__isnull=True) | Q(odoo_id=""))

    class Meta:
        model = Product
        fields = [
            "category",
            "product_template",
            "brand",
            "min_price",
            "max_price",
            "is_top",
            "attributes",
        ]


class ProductTemplateFilter(filters.FilterSet):
    odoo_id = filters.CharFilter(field_name="odoo_id", lookup_expr="exact")

    is_top = filters.BooleanFilter(
        field_name="is_top", label=_("Top Product Template")
    )

    has_odoo_id = filters.BooleanFilter(
        method="filter_has_odoo_id", label=_("Has Odoo ID")
    )

    price_min = filters.NumberFilter(
        field_name="price", lookup_expr="gte", label=_("Minimum Price")
    )
    price_max = filters.NumberFilter(
        field_name="price", lookup_expr="lte", label=_("Maximum Price")
    )

    on_hand_min = filters.NumberFilter(
        field_name="on_hand", lookup_expr="gte", label=_("Minimum Stock")
    )
    on_hand_max = filters.NumberFilter(
        field_name="on_hand", lookup_expr="lte", label=_("Maximum Stock")
    )

    search = filters.CharFilter(
        method="filter_by_search", label=_("Search")
    )  # Changed from 'name' to 'search'

    category = filters.ModelChoiceFilter(
        queryset=Category.objects.all(),
        method="filter_by_category_with_children",
        label=_("Category or Subcategories"),
    )

    brand = filters.ModelChoiceFilter(queryset=Brand.objects.all(), label=_("Brand"))
    branch = filters.ModelChoiceFilter(queryset=Branch.objects.all(), label=_("Branch"))

    created_at_after = filters.DateTimeFilter(
        field_name="created_at", lookup_expr="gte", label=_("Created After")
    )
    created_at_before = filters.DateTimeFilter(
        field_name="created_at", lookup_expr="lte", label=_("Created Before")
    )

    updated_at_after = filters.DateTimeFilter(
        field_name="updated_at", lookup_expr="gte", label=_("Updated After")
    )
    updated_at_before = filters.DateTimeFilter(
        field_name="updated_at", lookup_expr="lte", label=_("Updated Before")
    )

    attributes = filters.ModelMultipleChoiceFilter(
        field_name="products__attributes",
        queryset=Option.objects.all(),
        label="Attributes",
    )

    def filter_by_category_with_children(self, queryset, name, value):
        if not value:
            return queryset

        def get_all_children(cat):
            children = list(Category.objects.filter(parent=cat))
            for child in children[:]:  # copy for safe iteration
                children.extend(get_all_children(child))
            return children

        all_categories = [value] + get_all_children(value)
        return queryset.filter(category__in=all_categories)

    def filter_has_odoo_id(self, queryset, name, value):
        if value:
            return queryset.exclude(odoo_id__isnull=True).exclude(odoo_id="")
        else:
            return queryset.filter(Q(odoo_id__isnull=True) | Q(odoo_id=""))

    def filter_by_search(self, queryset, name, value):
        if not value:
            return queryset

        products = queryset.filter(Q(name__icontains=value))

        if not products.exists():
            products = (
                queryset.annotate(similarity=TrigramSimilarity("name", value))
                .filter(similarity__gt=0.2)
                .order_by("-similarity")
            )

        return products

    class Meta:
        model = ProductTemplate
        fields = [
            "odoo_id",
            "price_min",
            "price_max",
            "on_hand_min",
            "on_hand_max",
            "search",
            "category",
            "brand",
            "branch",
            "created_at_after",
            "created_at_before",
            "updated_at_after",
            "updated_at_before",
            "attributes",
            "is_top",
        ]


class CategoryFilter(filters.FilterSet):
    has_parent = filters.BooleanFilter(
        method="filter_has_parent", label="Has parent category"
    )
    parent_id = filters.NumberFilter(
        field_name="parent__id", lookup_expr="exact", label="Filter by Parent ID"
    )
    name = filters.CharFilter(
        method="filter_name", label="Name contains (in any language)"
    )
    odoo_id = filters.CharFilter(field_name="odoo_id", lookup_expr="exact")
    has_odoo_id = filters.BooleanFilter(
        method="filter_has_odoo_id", label="Has Odoo ID"
    )
    created_from = filters.DateTimeFilter(field_name="created_at", lookup_expr="gte")
    created_to = filters.DateTimeFilter(field_name="created_at", lookup_expr="lte")

    class Meta:
        model = Category
        fields = []

    def filter_has_parent(self, queryset, name, value):
        if value:
            return queryset.exclude(parent__isnull=True)
        return queryset.filter(parent__isnull=True)

    def filter_has_odoo_id(self, queryset, name, value):
        if value:
            return queryset.exclude(odoo_id__isnull=True).exclude(odoo_id="")
        return queryset.filter(Q(odoo_id__isnull=True) | Q(odoo_id=""))

    def filter_name(self, queryset, name, value):
        return queryset.filter(
            Q(name_uz__icontains=value)
            | Q(name_ru__icontains=value)
            | Q(name_en__icontains=value)
        )


class OrderFilter(filters.FilterSet):
    created_at__gte = filters.DateTimeFilter(field_name="created_at", lookup_expr="gte")
    created_at__lte = filters.DateTimeFilter(field_name="created_at", lookup_expr="lte")
    price__gte = filters.NumberFilter(field_name="price", lookup_expr="gte")
    price__lte = filters.NumberFilter(field_name="price", lookup_expr="lte")
    status = filters.CharFilter(field_name="status")
    payment_status = filters.CharFilter(field_name="payment_status")
    payment_method = filters.CharFilter(field_name="payment_method")
    type = filters.CharFilter(field_name="type")
    user = filters.NumberFilter(field_name="user__id")  # faqat adminlar uchun

    class Meta:
        model = Order
        fields = [
            "created_at__gte",
            "created_at__lte",
            "price__gte",
            "price__lte",
            "status",
            "payment_status",
            "payment_method",
            "type",
            "user",
        ]


class CarFilter(filters.FilterSet):
    created_at__gte = filters.DateTimeFilter(field_name="created_at", lookup_expr="gte")
    created_at__lte = filters.DateTimeFilter(field_name="created_at", lookup_expr="lte")
    updated_at__gte = filters.DateTimeFilter(field_name="updated_at", lookup_expr="gte")
    updated_at__lte = filters.DateTimeFilter(field_name="updated_at", lookup_expr="lte")

    firm = filters.NumberFilter(field_name="firm__id")
    firm_name = filters.CharFilter(field_name="firm__name", lookup_expr="icontains")
    model = filters.NumberFilter(field_name="model__id")
    model_name = filters.CharFilter(field_name="model__name", lookup_expr="icontains")

    number = filters.CharFilter(field_name="number", lookup_expr="icontains")

    user = filters.NumberFilter(field_name="user__id")

    class Meta:
        model = Car
        fields = [
            "created_at__gte",
            "created_at__lte",
            "updated_at__gte",
            "updated_at__lte",
            "firm",
            "firm_name",
            "model",
            "model_name",
            "number",
            "user",
        ]


class BrandFilter(filters.FilterSet):
    is_top = filters.BooleanFilter(field_name="is_top")

    class Meta:
        model = Brand
        fields = ["is_top"]


class ProductRatingFilter(filters.FilterSet):
    product_id = filters.NumberFilter(field_name="product__id")
    product_template_id = filters.NumberFilter(
        field_name="product__product_template__id",
        label="Filter by product template ID",
    )
    reviewer_id = filters.NumberFilter(field_name="reviewer__id")
    min_rating = filters.NumberFilter(field_name="rating", lookup_expr="gte")
    max_rating = filters.NumberFilter(field_name="rating", lookup_expr="lte")

    class Meta:
        model = ProductRating
        fields = ["product_id", "product_template_id", "reviewer_id", "rating"]


class CashbackFilter(filters.FilterSet):
    month = filters.NumberFilter(method="filter_by_month")
    year = filters.NumberFilter(method="filter_by_year")

    class Meta:
        model = Cashback
        fields = ["state", "balance", "month", "year"]

    def filter_by_month(self, queryset, name, value):
        return queryset.annotate(month=ExtractMonth("created_at")).filter(month=value)

    def filter_by_year(self, queryset, name, value):
        return queryset.annotate(year=ExtractYear("created_at")).filter(year=value)
