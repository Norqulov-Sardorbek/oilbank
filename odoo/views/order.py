from app.models.order import (
    Order,
    OrderItem,
    OrderRating,
    Basket,
    BasketItem,
    Region,
    District,
    DeliveryPrice,
    RatingType, 
    LoyaltyProgram, 
    PromoReward, 
    PromoCode,
    LoyaltyRule,
)
from ..serializers.order import (
    ReginSerializer,
    DistrictSerializer,
    DeliveryPriceSerializer,
    OrderSerializer,
    OrderItemSerializer,
    OrderRatingSerializer,
    RatingTypeSerializer, 
    LoyaltyProgramSerializer, 
    PromoRewardSerializer, 
    PromoCodeSerializer,
    LoyaltyRuleSerializer,
)
from rest_framework import status
from rest_framework.response import Response
from ..custom_filter import OdooIDFilterSet
from rest_framework.permissions import AllowAny
from .custom_base_viewset import OdooBaseViewSet
import logging, json
logger = logging.getLogger(__name__) 


class RegionViewSet(OdooBaseViewSet):
    permission_classes = [AllowAny]
    queryset = Region.objects.all()
    serializer_class = ReginSerializer
    filterset_class = OdooIDFilterSet
    lookup_field = "odoo_id"


class DistrictViewSet(OdooBaseViewSet):
    permission_classes = [AllowAny]
    queryset = District.objects.all()
    serializer_class = DistrictSerializer
    filterset_class = OdooIDFilterSet
    lookup_field = "odoo_id"


class DeliveryPriceViewSet(OdooBaseViewSet):
    permission_classes = [AllowAny]
    queryset = DeliveryPrice.objects.all()
    serializer_class = DeliveryPriceSerializer
    filterset_class = OdooIDFilterSet
    lookup_field = "odoo_id"


class OrderViewSet(OdooBaseViewSet):
    permission_classes = [AllowAny]
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    filterset_class = OdooIDFilterSet
    lookup_field = "odoo_id"

    def _invalid_response(self, serializer):
        logger.error("Order serializer errors → %s", serializer.errors)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return self._invalid_response(serializer)
        print(f"\n\n\n\n\n\n\n Incoming Create data from {self.__class__.__name__}", request.data)

        logger.info("Incoming Order POST → %s", request.data)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        print(f"\n\n\n\n\n\n\n Incoming Update data from {self.__class__.__name__}", request.data)

        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=False)
        if not serializer.is_valid():
            return self._invalid_response(serializer)

        self.perform_update(serializer)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        if not serializer.is_valid():
            return self._invalid_response(serializer)

        self.perform_update(serializer)
        return Response(serializer.data, status=status.HTTP_200_OK)


class OrderItemViewSet(OdooBaseViewSet):
    permission_classes = [AllowAny]
    queryset = OrderItem.objects.all()
    serializer_class = (
        OrderItemSerializer  # Assuming you have a serializer for OrderItem
    )
    filterset_class = OdooIDFilterSet
    lookup_field = "odoo_id"

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        print("\n\n\n\n\n\n\nIncoming Order Item POST data:", request.data)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )


class RatingViewSet(OdooBaseViewSet):
    permission_classes = [AllowAny]
    queryset = RatingType.objects.all()
    serializer_class = RatingTypeSerializer
    filterset_class = OdooIDFilterSet
    lookup_field = "odoo_id"


class OrderRatingViewSet(OdooBaseViewSet):
    permission_classes = [AllowAny]
    queryset = OrderRating.objects.all()
    serializer_class = OrderRatingSerializer
    filterset_class = OdooIDFilterSet
    lookup_field = "odoo_id"

class LoyaltyProgramViewSet(OdooBaseViewSet):
    permission_classes = [AllowAny]
    queryset = LoyaltyProgram.objects.all()
    serializer_class = LoyaltyProgramSerializer
    filterset_class = OdooIDFilterSet
    lookup_field = "odoo_id"

class PromoRewardViewSet(OdooBaseViewSet):
    permission_classes = [AllowAny]
    queryset = PromoReward.objects.all()
    serializer_class = PromoRewardSerializer
    filterset_class = OdooIDFilterSet
    lookup_field = "odoo_id"

class PromoCodeViewSet(OdooBaseViewSet):
    permission_classes = [AllowAny]
    queryset = PromoCode.objects.all()
    serializer_class = PromoCodeSerializer
    filterset_class = OdooIDFilterSet
    lookup_field = "odoo_id"

    def create(self, request, *args, **kwargs):
        many = isinstance(request.data, list)
        serializer = self.get_serializer(data=request.data, many=many)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=201)


class LoyaltyRuleViewSet(OdooBaseViewSet):
    permission_classes = [AllowAny]
    queryset = LoyaltyRule.objects.all()
    serializer_class = LoyaltyRuleSerializer
    filterset_class = OdooIDFilterSet
    lookup_field = "odoo_id"
