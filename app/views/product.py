from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    extend_schema_view,
    extend_schema,
    OpenApiExample,
    OpenApiResponse,
    OpenApiParameter,
    inline_serializer,
)
from rest_framework import permissions, viewsets, serializers
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q, Count, F
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.exceptions import ParseError
from django.utils.translation import gettext_lazy as _

# local
from app.models.product import (
    SavedProduct,
    Product,
    Discount,
    Category,
    ProductTemplate,
    Brand,
    Offer,
    ProductRating,
    Variant,
    OilBrand,
    Option,
    Partner
)
from app.serializers.product import (
    SavedProductSerializer,
    DiscountSerializer,
    ProductSerializer,
    CategoryOutputSerializer,
    CategoryInputSerializer,
    BrandInputSerializer,
    BrandOutputSerializer,
    OfferGetSerializer,
    OfferCreateSerializer,
    ProductRatingSerializer,
    VariantoptionsSerializer,
    ProductTemplateListSerializer,
    ProductTemplateDetailSerializer,
    ProductGetSerializer,
    OilBrandSerializer,
    CategorySearchSerializer,
    ProductSearchSerializer,
    PartnerSerializer,
    PartnerGetSerializer
)
from app.permissions import (
    IsAdminOrReadOnly,
    AllowGetAnyOtherAuthenticated,
    OptionalJWTAuthentication,
)
from app.custom_filters import (
    ProductFilter,
    ProductTemplateFilter,
    CategoryFilter,
    BrandFilter,
    ProductRatingFilter,
)
from utils.pagination.paginations import DefaultLimitOffSetPagination
from django.contrib.postgres.search import TrigramSimilarity
import logging

logger = logging.getLogger(__name__)


@extend_schema(
    summary="List Saved Products",
    description="Retrieve a list of products that the authenticated user has saved.",
    responses={200: SavedProductSerializer(many=True)},
)
class SavedProductListView(ListAPIView):
    serializer_class = SavedProductSerializer
    pagination_class = DefaultLimitOffSetPagination
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return SavedProduct.objects.filter(user=self.request.user)


@extend_schema(
    summary="Toggle Saved Product",
    description=(
        "Toggle the saved status of a product for the authenticated user. "
        "If the product is not already saved, it will be saved. "
        "If it is already saved, it will be removed."
    ),
    request={
        "application/json": {
            "type": "object",
            "properties": {
                "product_id": {
                    "type": "integer",
                    "description": "ID of the product to toggle.",
                }
            },
            "required": ["product_id"],
        }
    },
    responses={
        201: SavedProductSerializer,
        204: OpenApiResponse(
            description="Product successfully removed from saved list."
        ),
        400: OpenApiResponse(description="Product ID is required."),
        404: OpenApiResponse(description="Product not found."),
    },
)
class SavedProductToggleView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        product_id = request.data.get("product_id")

        if not product_id:
            return Response(
                {"error": "Product template ID is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            product = ProductTemplate.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response(
                {"error": "Product template not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        saved_product, created = SavedProduct.objects.get_or_create(
            user=request.user, product_template=product
        )

        if not created:
            saved_product.delete()
            return Response(
                {"message": "Product template removed from saved"},
                status=status.HTTP_204_NO_CONTENT,
            )

        return Response(
            SavedProductSerializer(saved_product).data, status=status.HTTP_201_CREATED
        )


@extend_schema(
    summary="Bulk Toggle Saved Products",
    description=(
        "Toggle the saved status of multiple products for the authenticated user. "
        "For each product: if it's not already saved, it will be saved. "
        "If it is already saved, it will be removed."
    ),
    request={
        "application/json": {
            "type": "object",
            "properties": {
                "product_ids": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "List of product IDs to toggle.",
                }
            },
            "required": ["product_ids"],
        }
    },
    responses={
        200: inline_serializer(
            name="BulkSavedProductResponse",
            fields={
                "added": inline_serializer(
                    name="AddedProduct",
                    many=True,
                    fields={
                        "id": serializers.IntegerField(),
                        "product_template": serializers.IntegerField(),
                    },
                ),

                "not_found": serializers.ListField(
                    child=serializers.IntegerField(),
                    help_text="List of product IDs that were not found"
                ),
            },
        ),
        400: OpenApiResponse(description="Product IDs list is required."),
    },
)
class BulkSavedProductToggleView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        product_ids = request.data.get("product_ids")

        if not product_ids or not isinstance(product_ids, list):
            return Response(
                {"error": "Product IDs list is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        added = []
        not_found = []

        for product_id in product_ids:
            try:
                product = ProductTemplate.objects.get(id=product_id)
            except ProductTemplate.DoesNotExist:
                not_found.append(product_id)
                continue

            saved_product, created = SavedProduct.objects.get_or_create(
                user=request.user, product_template=product
            )
            if created:
                added.append(SavedProductSerializer(saved_product).data)

        return Response(
            {
                "added": added,
                "not_found": not_found,
            },
            status=status.HTTP_200_OK,
        )



@extend_schema_view(
    list=extend_schema(
        summary="List active discounts",
        description=(
            "Returns all discounts that are either global or belong to the "
            "authenticated user and whose validity period includes now."
        ),
        responses={200: DiscountSerializer(many=True)},
    ),
    retrieve=extend_schema(
        summary="Retrieve a discount",
        description="Returns detailed information about a single discount.",
        responses={200: DiscountSerializer},
    ),
)
class DiscountViewset(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAdminOrReadOnly]
    serializer_class = DiscountSerializer
    pagination_class = DefaultLimitOffSetPagination

    def get_queryset(self):
        user = self.request.user
        now = timezone.now()
        return Discount.objects.filter(
            Q(user=None) | Q(user=user), time_from__lte=now, time_to__gte=now
        ).order_by("time_from")


@extend_schema_view(
    list=extend_schema(
        summary="List categories",
        description=(
            "Returns a list of categories. "
            "Supports filtering (has_parent, name, odoo_id, has_odoo_id, created_from/created_to), "
            "search (name_uz/ru/en) and ordering."
        ),
        responses={200: CategoryOutputSerializer(many=True)},
    ),
    retrieve=extend_schema(
        summary="Retrieve a category",
        description="Returns details of a single category by its ID.",
        responses={200: CategoryOutputSerializer},
    ),
    create=extend_schema(
        summary="Create a category",
        description="Creates a new category (admin only). Up to 3 levels deep.",
        request=CategoryInputSerializer,
        responses={201: CategoryOutputSerializer},
        examples=[
            OpenApiExample(
                "Example request",
                value={
                    "name_uz": "Telefonlar",
                    "name_ru": "Телефоны",
                    "name_en": "Phones",
                    "parent": None,
                },
                request_only=True,
            )
        ],
    ),
    update=extend_schema(
        summary="Replace a category",
        description="Updates all fields of a category (admin only).",
        request=CategoryInputSerializer,
        responses={200: CategoryOutputSerializer},
    ),
    partial_update=extend_schema(
        summary="Partially update category",
        description="Updates one or more fields of a category (admin only).",
        request=CategoryInputSerializer,
        responses={200: CategoryOutputSerializer},
    ),
    destroy=extend_schema(
        summary="Delete category",
        description="Deletes a category by its ID (admin only).",
        responses={204: None},
    ),
)
class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.filter(is_visible=False)
    permission_classes = [IsAdminOrReadOnly]
    authentication_classes = [OptionalJWTAuthentication]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = CategoryFilter
    search_fields = ["name_uz", "name_ru", "name_en"]
    ordering_fields = ["created_at", "updated_at", "id"]

    def get_serializer_class(self):
        if self.request.method in ["GET", "HEAD", "OPTIONS"]:
            return CategoryOutputSerializer
        return CategoryInputSerializer


@extend_schema_view(
    list=extend_schema(
        summary="List brands",
        description="Returns a list of available brands.",
        responses={200: BrandOutputSerializer(many=True)},
    ),
    retrieve=extend_schema(
        summary="Retrieve a brand",
        description="Returns details of a single brand by its ID.",
        responses={200: BrandOutputSerializer},
    ),
    create=extend_schema(
        summary="Create a brand",
        description="Creates a new brand (admin only).",
        request=BrandInputSerializer,
        responses={201: BrandOutputSerializer},
        examples=[
            OpenApiExample(
                "Example request",
                value={
                    "name_uz": "Chevrolet",
                    "name_ru": "Шевроле",
                    "name_en": "Chevrolet",
                    "image": None,
                },
                request_only=True,
            )
        ],
    ),
    update=extend_schema(
        summary="Replace a brand",
        description="Updates all fields of a brand (admin only).",
        request=BrandInputSerializer,
        responses={200: BrandOutputSerializer},
    ),
    partial_update=extend_schema(
        summary="Partially update brand",
        description="Updates one or more fields of a brand (admin only).",
        request=BrandInputSerializer,
        responses={200: BrandOutputSerializer},
    ),
    destroy=extend_schema(
        summary="Delete brand",
        description="Deletes a brand by its ID (admin only).",
        responses={204: None},
    ),
)
class BrandViewSet(viewsets.ModelViewSet):
    queryset = Brand.objects.all()
    permission_classes = [IsAdminOrReadOnly]
    authentication_classes = [OptionalJWTAuthentication]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = BrandFilter
    search_fields = ["name_uz", "name_ru", "name_en"]
    ordering_fields = ["created_at", "updated_at", "id"]
    ordering = ["created_at"]  # Default ordering: oldest first, newest last

    def get_serializer_class(self):
        if self.request.method in ["GET", "HEAD", "OPTIONS"]:
            return BrandOutputSerializer
        return BrandInputSerializer


class OilBrandViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = OilBrand.objects.all()
    serializer_class = OilBrandSerializer
    permission_classes = [IsAdminOrReadOnly]
    authentication_classes = [OptionalJWTAuthentication]


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all().order_by("-updated_at")
    serializer_class = ProductSerializer
    pagination_class = DefaultLimitOffSetPagination
    permission_classes = [IsAdminOrReadOnly]
    authentication_classes = [OptionalJWTAuthentication]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ProductFilter
    search_fields = ["product_template__name", "description"]
    ordering_fields = ["price", "created_at", "updated_at"]
    ordering = ["price"]


@extend_schema_view(
    list=extend_schema(
        summary="List all product templates",
        description="Returns paginated list of product templates with basic information",
        responses={
            200: ProductTemplateListSerializer(many=True),
            400: OpenApiTypes.OBJECT,
        },
        examples=[
            OpenApiExample(
                "List response example",
                value=[
                    {
                        "id": 1,
                        "name": "Premium Engine Oil",
                        "image": "/media/product-templates/oil.jpg",
                        "price": "49.99",
                        "category": {"id": 1, "name_en": "Engine Oils"},
                    },
                    {
                        "id": 2,
                        "name": "Standard Engine Oil",
                        "image": "/media/product-templates/oil2.jpg",
                        "price": "29.99",
                        "category": {"id": 1, "name_en": "Engine Oils"},
                    },
                ],
                response_only=True,
            )
        ],
    ),
    retrieve=extend_schema(
        summary="Retrieve product template details",
        description="Get full details including variants, options and ratings for a product template",
        responses={
            200: ProductTemplateDetailSerializer,
            404: OpenApiTypes.OBJECT,
        },
        examples=[
            OpenApiExample(
                "Detailed response",
                value={
                    "id": 1,
                    "name": "Premium Engine Oil",
                    "description": "Synthetic engine oil for all weather conditions",
                    "price": "49.99",
                    "variants": [
                        {
                            "id": 1,
                            "name": "Viscosity",
                            "options": [
                                {"id": 1, "name": "5W-30"},
                                {"id": 2, "name": "10W-40"},
                            ],
                        }
                    ],
                    "recent_ratings": [
                        {
                            "id": 1,
                            "reviewer": 1,
                            "reviewer_name": "John Doe",
                            "product": 1,
                            "rating": 5,
                            "description": "Great product!",
                            "created_at": "2023-05-01T12:34:56Z",
                        }
                    ],
                    "average_rating": 4.5,
                },
                response_only=True,
            )
        ],
    ),
    create=extend_schema(
        summary="Create new product template",
        description="Admin-only endpoint to create new product templates",
        request=ProductTemplateDetailSerializer,
        responses={
            201: ProductTemplateDetailSerializer,
            400: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
        },
    ),
    update=extend_schema(
        summary="Update product template",
        description="Admin-only full update of product template",
        request=ProductTemplateDetailSerializer,
        responses={
            200: ProductTemplateDetailSerializer,
            400: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
    ),
    partial_update=extend_schema(
        summary="Partial update product template",
        description="Admin-only partial update of product template",
        request=ProductTemplateDetailSerializer,
        responses={
            200: ProductTemplateDetailSerializer,
            400: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
    ),
    destroy=extend_schema(
        summary="Delete product template",
        description="Admin-only deletion of product template",
        responses={
            204: None,
            403: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
    ),
    filter_options=extend_schema(
        summary="Filter product variants and options",
        description="""
        Filter available product options based on selected variants.
        Returns available options and matched product if all variants are selected.

        Query format: ?variant_id=option_id
        Example: ?1=5&2=8 (Variant 1 → Option 5, Variant 2 → Option 8)
        """,
        parameters=[
            OpenApiParameter(
                name="variant_id",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Variant ID as parameter name, Option ID as value",
                examples=[
                    OpenApiExample(
                        "Single variant example",
                        value={"1": "5"},
                        description="Filter by variant 1 with option 5",
                    ),
                    OpenApiExample(
                        "Multiple variants example",
                        value={"1": "5", "2": "8"},
                        description="Filter by variant 1 (option 5) and variant 2 (option 8)",
                    ),
                ],
            )
        ],
        responses={
            200: inline_serializer(
                name="FilterOptionsResponse",
                fields={
                    "available_options": inline_serializer(
                        name="AvailableVariantOptions",
                        many=True,
                        fields={
                            "id": serializers.IntegerField(),
                            "name": serializers.CharField(),
                            "options": inline_serializer(
                                name="OptionAvailability",
                                many=True,
                                fields={
                                    "id": serializers.IntegerField(),
                                    "name": serializers.CharField(),
                                    "available": serializers.BooleanField(),
                                },
                            ),
                        },
                    ),
                    "matched_product": inline_serializer(
                        name="MatchedProduct",
                        fields={
                            "id": serializers.IntegerField(),
                            "name": serializers.CharField(),
                            "price": serializers.DecimalField(
                                decimal_places=2, max_digits=10
                            ),
                            "image": serializers.ImageField(),
                        },
                        allow_null=True,
                    ),
                },
            ),
            400: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        examples=[
            OpenApiExample(
                "Partial selection response",
                value={
                    "available_options": [
                        {
                            "id": 1,
                            "name": "Viscosity",
                            "options": [
                                {"id": 5, "name": "5W-30", "available": True},
                                {"id": 6, "name": "10W-40", "available": False},
                            ],
                        },
                        {
                            "id": 2,
                            "name": "Size",
                            "options": [
                                {"id": 7, "name": "1L", "available": True},
                                {"id": 8, "name": "5L", "available": True},
                            ],
                        },
                    ],
                    "matched_product": None,
                },
                response_only=True,
                status_codes=["200"],
            ),
            OpenApiExample(
                "Full match response",
                value={
                    "available_options": [
                        {
                            "id": 1,
                            "name": "Viscosity",
                            "options": [{"id": 5, "name": "5W-30", "available": True}],
                        }
                    ],
                    "matched_product": {
                        "id": 123,
                        "name": "Premium Oil 5W-30 1L",
                        "price": "49.99",
                        "image": "http://127.0.0.1:8000/media/products/123.jpg",
                    },
                },
                response_only=True,
                status_codes=["200"],
            ),
        ],
    ),
)
class ProductTemplateViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminOrReadOnly]
    authentication_classes = [OptionalJWTAuthentication]
    queryset = ProductTemplate.objects.filter(is_visible=False).order_by("-updated_at")
    pagination_class = DefaultLimitOffSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = ProductTemplateFilter

    def get_serializer_class(self):
        if self.action == "list":
            return ProductTemplateListSerializer
        return ProductTemplateDetailSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action in ["retrieve", "update", "partial_update"]:
            queryset = queryset.prefetch_related(
                "product_template_options__variant",
                "product_template_options__product_options",
                "product_template_options__variant__variant_option",
                "product_options",
            )
        return queryset

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="variant_id:option_id (query format)",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description=(
                    "Dynamic query params in the form of variant_id=option_id or variant_id:option_id. "
                    "Examples: ?14=46 or ?variant_id:option_id=14:46 means Variant ID 14 → Option ID 46"
                ),
                required=False,
                many=False,
            )
        ],
        responses={200: OpenApiTypes.OBJECT},
        description="Filter options and return available options (with selected and stock status) and matched product based on selected options",
    )
    @action(detail=True, methods=["get"], url_path="filter")
    def filter_options(self, request, pk=None):
        product_template = self.get_object()

        # Parse query params into variant_id: option_id
        selected = {}
        for key, value in request.query_params.items():
            try:
                if key.isdigit() and value.isdigit():
                    # Format: ?14=46
                    selected[int(key)] = int(value)
                elif ":" in value and key == "variant_id:option_id (query format)":
                    # Format: ?variant_id:option_id (query format)=14:46
                    variant_id, option_id = map(int, value.split(":"))
                    selected[variant_id] = option_id
                else:
                    logger.warning(f"Invalid query param format: {key}={value}")
            except (ValueError, TypeError) as e:
                logger.warning(f"Failed to parse query param {key}={value}: {e}")
                continue

        selected_option_ids = list(selected.values())
        selected_variant_ids = list(selected.keys())

        # Validate variant and option IDs
        for variant_id, option_id in selected.items():
            if not Variant.objects.filter(
                id=variant_id,
                product_template_variants__product_template=product_template,
            ).exists():
                logger.error(
                    f"Invalid variant ID: {variant_id} for product template {pk}"
                )
                return Response(
                    {"error": f"Invalid variant ID: {variant_id}"}, status=400
                )
            if not Option.objects.filter(id=option_id, variant_id=variant_id).exists():
                logger.error(f"Invalid option ID: {option_id} for variant {variant_id}")
                return Response(
                    {
                        "error": f"Invalid option ID: {option_id} for variant {variant_id}"
                    },
                    status=400,
                )

        # Get all variants for this product template
        variants = (
            Variant.objects.filter(
                product_template_variants__product_template=product_template
            )
            .distinct()
            .prefetch_related("variant_option")
        )

        # Determine available options for each variant
        available_options = []
        for variant in variants:
            options_data = []
            for option in variant.variant_option.all():
                # Build filter conditions excluding the current variant's selected option
                filter_conditions = Q()
                for v_id, o_id in selected.items():
                    if v_id != variant.id:  # Exclude the current variant
                        filter_conditions &= Q(attributes__id=o_id)

                # Check if a product exists with this option and other selected options
                is_available = False
                is_in_stock = False
                product_query = Product.objects.filter(
                    attributes__id=option.id, product_template=product_template
                )
                if filter_conditions:
                    product_query = product_query.filter(filter_conditions)

                # Check availability
                is_available = product_query.exists()

                # Check stock if available
                if is_available:
                    is_in_stock = product_query.filter(
                        stock_quants__quantity__gt=F("stock_quants__reserved_quantity")
                    ).exists()

                # Check if this option is selected
                is_selected = option.id in selected_option_ids

                options_data.append(
                    {
                        "id": option.id,
                        "name": option.name,
                        "available": is_available,
                        "selected": is_selected,
                        "in_stock": is_in_stock,
                    }
                )

            available_options.append(
                {"id": variant.id, "name": variant.name, "options": options_data}
            )

        # Exact match for products
        matched_product_data = None
        if len(selected_variant_ids) == variants.count():
            filtered_products = (
                Product.objects.filter(
                    product_template=product_template,
                    attributes__id__in=selected_option_ids,
                )
                .annotate(attr_count=Count("attributes"))
                .filter(attr_count=len(selected_option_ids))
            )
            matched = filtered_products.first()
            if matched:
                logger.debug(
                    f"Matched product found: ID {matched.id} with attributes {list(matched.attributes.values('id', 'name'))}"
                )
                matched_product_data = ProductGetSerializer(
                    matched, context={"request": request}
                ).data
            else:
                logger.warning(
                    f"No product matched for template {pk} with options {selected_option_ids}"
                )

        return Response(
            {
                "available_options": available_options,
                "matched_product": matched_product_data,
            }
        )


@extend_schema_view(
    list=extend_schema(
        summary="List all offers",
        description="Returns a list of all offers with related product data (name from product template).",
        responses={200: OfferGetSerializer(many=True)},
    ),
    retrieve=extend_schema(
        summary="Retrieve a specific offer",
        description="Retrieve offer detail by ID with all related products.",
        responses={200: OfferGetSerializer},
    ),
    create=extend_schema(
        summary="Create a new offer",
        description="Create a new offer with start and end dates and assigned products.",
        request=OfferGetSerializer,
        responses={201: OfferGetSerializer},
        examples=[
            OpenApiExample(
                "Sample Create Offer",
                value={
                    "title": "New Year Offer",
                    "start_date": "2025-01-01",
                    "end_date": "2025-01-10",
                    "products": [1, 2],
                },
                request_only=True,
            )
        ],
    ),
    update=extend_schema(
        summary="Update an existing offer",
        description="Update all fields of an existing offer.",
        request=OfferGetSerializer,
        responses={200: OfferGetSerializer},
    ),
    partial_update=extend_schema(
        summary="Partially update an offer",
        description="Update some fields of an existing offer.",
        request=OfferGetSerializer,
        responses={200: OfferGetSerializer},
    ),
    destroy=extend_schema(
        summary="Delete an offer",
        description="Deletes the offer by ID.",
        responses={204: None},
    ),
)
class OfferViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminOrReadOnly]
    authentication_classes = [OptionalJWTAuthentication]
    serializer_class = OfferGetSerializer
    queryset = Offer.objects.all()

    def get_serializer_class(self):
        if self.action in ["create", "update"]:
            return OfferCreateSerializer
        return OfferGetSerializer


@extend_schema_view(
    list=extend_schema(
        summary="List product ratings",
        description="Get a list of product ratings. Authenticated users see their own ratings by default.",
        parameters=[
            OpenApiParameter(
                name="product_id",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Filter by product ID",
            ),
            OpenApiParameter(
                name="product_template_id",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Filter by product template ID",
            ),
            OpenApiParameter(
                name="reviewer_id",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Filter by reviewer ID (only available to authenticated users)",
            ),
            OpenApiParameter(
                name="min_rating",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Filter by minimum rating (1-5)",
            ),
            OpenApiParameter(
                name="max_rating",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Filter by maximum rating (1-5)",
            ),
        ],
        responses={
            200: ProductRatingSerializer(many=True),
            401: OpenApiTypes.OBJECT,
        },
        examples=[
            OpenApiExample(
                "Authenticated user example",
                value=[
                    {
                        "id": 1,
                        "reviewer": 123,
                        "product": 456,
                        "rating": 5,
                        "description": "Excellent product!",
                        "created_at": "2023-10-15T12:34:56Z",
                    }
                ],
                response_only=True,
            ),
            OpenApiExample(
                "Anonymous user example",
                value=[
                    {
                        "id": 2,
                        "product": 456,
                        "rating": 4,
                        "description": "Good product",
                        "created_at": "2023-10-14T10:30:00Z",
                    }
                ],
                response_only=True,
                description="Anonymous users don't see reviewer info",
            ),
        ],
    ),
    retrieve=extend_schema(
        summary="Retrieve product rating",
        description="Get details of a specific product rating.",
        responses={
            200: ProductRatingSerializer,
            404: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
        },
    ),
    create=extend_schema(
        summary="Create product rating",
        description="Create a new product rating. Requires authentication.",
        request=ProductRatingSerializer,
        responses={
            201: ProductRatingSerializer,
            400: inline_serializer(
                name="RatingCreateError",
                fields={
                    "detail": serializers.CharField(),
                    "product_id": serializers.CharField(required=False),
                },
            ),
            401: OpenApiTypes.OBJECT,
        },
        examples=[
            OpenApiExample(
                "Valid request",
                value={
                    "product": 456,
                    "rating": 5,
                    "description": "Excellent product!",
                },
                request_only=True,
            ),
            OpenApiExample(
                "Missing product",
                value={"detail": "Product ID is required."},
                response_only=True,
                status_codes=["400"],
            ),
        ],
    ),
    update=extend_schema(
        summary="Update product rating",
        description="Full update of a product rating. Only the rating owner can update.",
        request=ProductRatingSerializer,
        responses={
            200: ProductRatingSerializer,
            400: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
    ),
    partial_update=extend_schema(
        summary="Partial update product rating",
        description="Partial update of a product rating. Only the rating owner can update.",
        request=ProductRatingSerializer,
        responses={
            200: ProductRatingSerializer,
            400: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
    ),
    destroy=extend_schema(
        summary="Delete product rating",
        description="Delete a product rating. Only the rating owner can delete.",
        responses={
            204: None,
            403: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
    ),
)
class ProductRatingViewSet(viewsets.ModelViewSet):
    queryset = ProductRating.objects.all().order_by("-created_at")
    serializer_class = ProductRatingSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = ProductRatingFilter
    http_method_names = ["get", "post"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return self.queryset.none()

        queryset = super().get_queryset()
        user = self.request.user

        # For authenticated users, include their ratings by default
        if user.is_authenticated:
            # If no specific reviewer filter is applied, show only current user's ratings
            if "reviewer_id" not in self.request.query_params:
                queryset = queryset.filter(reviewer=user)
        else:
            # For anonymous users, only allow GET requests
            if self.request.method != "GET":
                return ProductRating.objects.none()

        return queryset

    def perform_create(self, serializer):
        serializer.save(reviewer=self.request.user)

    def perform_update(self, serializer):
        # Ensure the reviewer cannot be changed
        serializer.save(reviewer=self.request.user)

    def create(self, request, *args, **kwargs):
        super().create(request, *args, **kwargs)
        return Response({"message": _("Product has been rated")}, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.reviewer == request.user:
            super().destroy(request, *args, **kwargs)
            return Response({"message": _("Product rating has been deleted")}, status=status.HTTP_204_NO_CONTENT)
        else:
            return Response({"detail": "You can't delete this product rating."}, status=status.HTTP_400_BAD_REQUEST)


class VariantViewSet(viewsets.ReadOnlyModelViewSet):

    queryset = Variant.objects.filter(variant_option__isnull=False).distinct()
    serializer_class = VariantoptionsSerializer
    permission_classes = [IsAdminOrReadOnly]
    authentication_classes = [OptionalJWTAuthentication]
    # pagination_class = DefaultLimitOffSetPagination


class SimilarProductViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Viewset to get similar products based on category and brand.
    """

    serializer_class = ProductTemplateDetailSerializer
    permission_classes = [IsAdminOrReadOnly]
    authentication_classes = [OptionalJWTAuthentication]
    pagination_class = DefaultLimitOffSetPagination

    def get_queryset(self):
        # Get product_ids from URL path parameter instead of query params
        product_ids_str = self.kwargs.get("product_ids", "")
        
        try:
            product_ids = [
                int(pid.strip()) for pid in product_ids_str.split(",") if pid.strip()
            ]
        except ValueError:
            raise ParseError({"error": "Invalid product ID list."})
        
        print(f"\n\nn\nReceived product IDs: {product_ids}\n\n\n")

        products = Product.objects.filter(id__in=product_ids).select_related(
            "product_template__category", "product_template__brand"
        )
        print("\n\nn\nFiltered products:\n", products)

        if not products.exists():
            return ProductTemplate.objects.none()
            
        # Get category and brand IDs (not objects)
        category_ids = {
            p.product_template.category.pk
            for p in products 
            if p.product_template.category is not None
        }
        brand_ids = {
            p.product_template.brand.pk 
            for p in products 
            if p.product_template.brand is not None
        }

        conditions = Q()
        
        if category_ids:
            conditions |= Q(category__in=category_ids)
        
        if brand_ids:
            conditions |= Q(brand__in=brand_ids)
        
        # If no categories or brands found, return empty queryset
        if not conditions:
            return ProductTemplate.objects.none()

        # Get similar templates that are visible (fixed: changed to is_visible=True)
        similar_templates = ProductTemplate.objects.filter(
            conditions & Q(is_visible=False)  # Only visible products
        )

        # Exclude original templates
        original_template_ids = {p.product_template.pk for p in products}
        similar_templates = similar_templates.exclude(id__in=original_template_ids)

        return similar_templates.distinct()

    def list(self, request, *args, **kwargs):
        try:
            queryset = self.filter_queryset(self.get_queryset())
        except ParseError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    

class SimilarProductTemplatesViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Viewset to get similar products based on category and brand.
    """

    serializer_class = ProductTemplateDetailSerializer
    permission_classes = [IsAdminOrReadOnly]
    authentication_classes = [OptionalJWTAuthentication]
    pagination_class = DefaultLimitOffSetPagination

    def get_queryset(self):
        product_ids_str = self.request.query_params.get("product_ids", "")
        try:
            product_ids = [
                int(pid.strip()) for pid in product_ids_str.split(",") if pid.strip()
            ]
        except ValueError:
            raise ParseError({"error": "Invalid product ID list."})

        # Fix 1: Correct select_related field names
        products = ProductTemplate.objects.filter(id__in=product_ids).select_related(
            "category", "brand"
        )

        if not products.exists():
            return ProductTemplate.objects.none()

        # Fix 2: Extract IDs instead of model instances
        category_ids = {p.category.pk for p in products if p.category}
        brand_ids = {p.branch.pk for p in products if p.branch}

        # Fix 3: Only filter by category and brand, remove is_visible=False condition
        # unless you specifically want to include invisible products
        similar_templates = ProductTemplate.objects.filter(
            Q(category__in=category_ids) | Q(brand__in=brand_ids)
        )

        # Exclude the original products from results
        original_template_ids = {p.pk for p in products}
        similar_templates = similar_templates.exclude(id__in=original_template_ids)

        # Optional: Only return visible products (add this if needed)
        similar_templates = similar_templates.filter(is_visible=False)

        return similar_templates.distinct()

    def list(self, request, *args, **kwargs):
        try:
            queryset = self.filter_queryset(self.get_queryset())
        except ParseError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class SearchAPIView(ListAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = CategorySearchSerializer

    def get_queryset(self):
        query = self.request.query_params.get("q", "").strip()
        limit = self.request.query_params.get("limit", 5)
        try:
            limit = int(limit)
            if limit < 1:
                limit = 5
        except ValueError:
            limit = 5

        top_level_categories = Category.objects.filter(parent__isnull=True)
        category_data = []
        product_data = []

        if query:
            # Apply exclude before slicing
            products = ProductTemplate.objects.filter(
                Q(name__icontains=query)
            ).exclude(is_visible=True)[:limit]

            if not products.exists():
                similar_products = (
                    ProductTemplate.objects.annotate(
                        similarity=TrigramSimilarity("name", query)
                    )
                    .exclude(is_visible=True)
                    .filter(similarity__gt=0.2)
                    .order_by("-similarity")[:limit]
                )
                products = similar_products

            if products.exists():
                product_data.extend(products)
                for product in products:
                    category = product.category
                    while category and category.parent:
                        category = category.parent
                    if category and category not in category_data:
                        category_data.append(category)

        return category_data

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        category_serializer = self.get_serializer(queryset, many=True)
        product_serializer = ProductSearchSerializer(
            self.get_queryset_products(), many=True
        )
        return Response(
            {
                "categories": category_serializer.data,
                "products": product_serializer.data,
            }
        )

    def get_queryset_products(self):
        query = self.request.query_params.get("q", "").strip()
        limit = self.request.query_params.get("limit", 5)
        try:
            limit = int(limit)
            if limit < 1:
                limit = 5
        except ValueError:
            limit = 5

        product_data = []

        if query:
            # Apply exclude before slicing
            products = ProductTemplate.objects.filter(
                Q(name__icontains=query)
            ).exclude(is_visible=True)[:limit]

            if not products.exists():
                similar_products = (
                    ProductTemplate.objects.annotate(
                        similarity=TrigramSimilarity("name", query)
                    )
                    .exclude(is_visible=True)
                    .filter(similarity__gt=0.2)
                    .order_by("-similarity")[:limit]
                )
                products = similar_products

            product_data.extend(products)

        return product_data


class PartnerViewSet(viewsets.ModelViewSet):
    """
    Viewset for managing partners.
    """

    queryset = Partner.objects.all().order_by("-updated_at")
    serializer_class = PartnerSerializer
    permission_classes = [IsAdminOrReadOnly]
    authentication_classes = [OptionalJWTAuthentication]
    pagination_class = DefaultLimitOffSetPagination

    def get_serializer_class(self):
        if self.action in ["list", "retrieve"]:
            return PartnerGetSerializer
        return PartnerSerializer

    def perform_create(self, serializer):
        serializer.save()

    def perform_update(self, serializer):
        serializer.save()