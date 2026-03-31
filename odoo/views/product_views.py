from rest_framework.views import APIView
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
    Pricelist,
    Discount,
    Currency,
    OilBrand,
    FilterBrand,
    Brand,
    ProductTemplateImage,
    Offer,
    Partner,
)
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from odoo.serializers.product_serializer import (
    VariantSerializer,
    OptionSerializer,
    ProductOptionSerializer,
    ProductVariantsSerializer,
    ProductTemplateSerializer,
    WareHouseSerializer,
    ProductSerializer,
    LocationSerializer,
    ProductVariantGerSerialzier,
    CategorySerializer,
    StockQuantSerializer,
    CurrencySerializer,
    PricelistSerializer,
    DiscountSerializer,
    OilBrandSerializer,
    FilterBrandSerializer,
    BrandSerializer,
    ProductTemplateImageSerializer,
    OfferSerializer,
    PartnerSerializer,
)
from ..custom_filter import OdooIDFilterSet
from .custom_base_viewset import OdooBaseViewSet


class BrandViewSet(OdooBaseViewSet):
    permission_classes = [AllowAny]
    queryset = Brand.objects.all()
    serializer_class = BrandSerializer
    # permission_classes = [IsAuthenticated]
    filterset_class = OdooIDFilterSet
    lookup_field = "odoo_id"


class VariantViewSet(OdooBaseViewSet):
    permission_classes = [AllowAny]
    queryset = Variant.objects.all()
    serializer_class = VariantSerializer
    # permission_classes = [IsAuthenticated]
    filterset_class = OdooIDFilterSet
    lookup_field = "odoo_id"


class ProductTemplateImageViewSet(OdooBaseViewSet):
    permission_classes = [AllowAny]
    serializer_class = ProductTemplateImageSerializer
    queryset = ProductTemplateImage.objects.all()
    filterset_class = OdooIDFilterSet
    lookup_field = 'odoo_id'

    def destroy(self, request, *args, **kwargs):
        print(f"\n\n\n\n\n\n\nIncoming Delete (delete) data:", request.data)
        return super().destroy(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        print(f"\n\n\n\n\n\n\nIncoming Update (update) data:", request.data)
        return super().update(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        print(f"\n\n\n\n\n\n\nIncoming Create (create) data:", request.data)
        return super().create(request, *args, **kwargs)


class OptionViewSet(OdooBaseViewSet):
    permission_classes = [AllowAny]
    queryset = Option.objects.all()
    serializer_class = OptionSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = OdooIDFilterSet
    lookup_field = "odoo_id"


class ProductOptionViewSet(OdooBaseViewSet):
    permission_classes = [AllowAny]
    queryset = ProductOption.objects.all()
    serializer_class = ProductOptionSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = OdooIDFilterSet
    lookup_field = "odoo_id"


class LocationViewSet(OdooBaseViewSet):
    permission_classes = [AllowAny]
    queryset = Location.objects.all()
    serializer_class = LocationSerializer
    # permission_classes = [IsAuthenticated]
    filterset_class = OdooIDFilterSet
    lookup_field = "odoo_id"


class ProductVariantsViewSet(OdooBaseViewSet):
    permission_classes = [AllowAny]
    queryset = ProductVariants.objects.all()
    # permission_classes = [IsAuthenticated]
    serializer_class = ProductVariantsSerializer
    filterset_class = OdooIDFilterSet
    lookup_field = "odoo_id"


class ProductTemplateViewSet(OdooBaseViewSet):
    permission_classes = [AllowAny]
    queryset = ProductTemplate.objects.all()
    # permission_classes = [IsAuthenticated]
    serializer_class = ProductTemplateSerializer
    filterset_class = OdooIDFilterSet
    lookup_field = "odoo_id"


class WareHouseViewSet(OdooBaseViewSet):
    permission_classes = [AllowAny]
    queryset = WareHouse.objects.all()
    # permission_classes = [IsAuthenticated]
    serializer_class = WareHouseSerializer
    filterset_class = OdooIDFilterSet
    lookup_field = "odoo_id"



class ProductViewSet(OdooBaseViewSet):
    permission_classes = [AllowAny]
    # permission_classes = [IsAuthenticated]
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filterset_class = OdooIDFilterSet
    lookup_field = "odoo_id"

class CategoryViewSet(OdooBaseViewSet):
    permission_classes = [AllowAny]
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    filterset_class = OdooIDFilterSet
    lookup_field = "odoo_id"


class StockQuantityViewSet(OdooBaseViewSet):
    permission_classes = [AllowAny]
    queryset = StockQuant.objects.all()
    serializer_class = StockQuantSerializer
    filterset_class = OdooIDFilterSet
    lookup_field = "odoo_id"


class PriceListViewSet(OdooBaseViewSet):
    permission_classes = [AllowAny]
    queryset = Pricelist.objects.all()
    serializer_class = PricelistSerializer
    filterset_class = OdooIDFilterSet
    lookup_field = "odoo_id"


class DiscountViewSet(OdooBaseViewSet):
    permission_classes = [AllowAny]
    queryset = Discount.objects.all()
    serializer_class = DiscountSerializer
    filterset_class = OdooIDFilterSet
    lookup_field = "odoo_id"


class CurrencyViewSet(OdooBaseViewSet):
    permission_classes = [AllowAny]
    queryset = Currency.objects.all()
    serializer_class = CurrencySerializer
    filterset_class = OdooIDFilterSet
    lookup_field = "odoo_id"


class OilBrandViewSet(OdooBaseViewSet):
    permission_classes = [AllowAny]
    queryset = OilBrand.objects.all()
    serializer_class = OilBrandSerializer
    filterset_class = OdooIDFilterSet
    lookup_field = "odoo_id"


class FilterBrandViewSet(OdooBaseViewSet):
    permission_classes = [AllowAny]
    queryset = FilterBrand.objects.all()
    serializer_class = FilterBrandSerializer
    filterset_class = OdooIDFilterSet
    lookup_field = "odoo_id"


class ProductOptionApi(APIView):
    permission_classes = [AllowAny]

    def update(self, request, *args, **kwargs):
        request_data = request.data
        line_id = request_data.get("line_id")
        if not line_id:
            return Response(
                {"error": "line_id is required"}, status=status.HTTP_400_BAD_REQUEST
            )
        value_id = request_data.get("value_id")
        if not value_id:
            return Response(
                {"error": "value_id is required"}, status=status.HTTP_400_BAD_REQUEST
            )
        attribute_value_id = request_data.get("attribute_value_id")
        if not attribute_value_id:
            return Response(
                {"error": "attribute_value_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        odoo_id = request_data.get("odoo_id")
        if not odoo_id:
            return Response(
                {"error": "odoo_id is required"}, status=status.HTTP_400_BAD_REQUEST
            )
        try:
            product_option = ProductOption.objects.select_related(
                "product_template_attribute_line", "option"
            ).get(
                product_template_attribute_line__odoo_id=line_id,
                option__odoo_id=value_id,
            )
            product_option.odoo_id = odoo_id
            product_option.send_odoo = False
            product_option.save()

        except ProductOption.DoesNotExist:
            return Response(
                {"error": "ProductOption not found"}, status=status.HTTP_404_NOT_FOUND
            )


class ProductDeleteApi(APIView):
    permission_classes = [AllowAny]

    def delete(self, request, *args, **kwargs):

        template_odoo_id = request.data.get("template_odoo_id")
        new_product_odoo_ids = request.data.get("e_ids")

        # Validate input
        if not template_odoo_id:
            return Response(
                {"error": "'template_odoo_id' is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not isinstance(new_product_odoo_ids, list):
            return Response(
                {"error": "'new_product_odoo_ids' must be a list"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Filter products to delete
        products_to_delete = Product.objects.filter(
            product_template__odoo_id=template_odoo_id
        ).exclude(odoo_id__in=new_product_odoo_ids)

        deleted_count = products_to_delete.count()

        if deleted_count == 0:
            return Response(
                {"message": "No products to delete"}, status=status.HTTP_200_OK
            )

        # Delete the filtered products
        products_to_delete.delete()

        return Response(
            {"message": f"{deleted_count} product(s) deleted successfully"},
            status=status.HTTP_200_OK,
        )


class OfferOdooViewSet(OdooBaseViewSet):
    permission_classes = [AllowAny]
    queryset = Offer.objects.all()
    serializer_class = OfferSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = OdooIDFilterSet
    lookup_field = "odoo_id"


class PartnerOdooViewSet(OdooBaseViewSet):
    permission_classes = [AllowAny]
    queryset = Partner.objects.all()
    serializer_class = PartnerSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = OdooIDFilterSet
    lookup_field = "odoo_id"     