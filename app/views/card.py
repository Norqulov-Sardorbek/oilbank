from drf_spectacular.types import OpenApiTypes
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.http import Http404
from drf_spectacular.utils import (
    extend_schema_view,
    extend_schema,
    OpenApiParameter,
    OpenApiExample,
)
from app.models.card import Card, Balance
from app.permissions import IsAdminOrReadOnly
from app.serializers.card import CardSerializer, CardBindSerializer, BalanceSerializer
from app.services.multicard import MulticardService
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from app.custom_filters import CashbackFilter

from app.models.card import BalanceStatus, Balance, Cashback
from app.serializers.card import (
    BalanceStatusSerializer,
    BalanceSerializer,
    CashbackSerializer,
)


@extend_schema_view(
    list=extend_schema(
        summary="List user's cards", responses=CardSerializer(many=True)
    ),
    retrieve=extend_schema(
        summary="Retrieve a specific card by ID",
        parameters=[
            OpenApiParameter(name="pk", description="Card ID", required=True, type=int)
        ],
    ),
    create=extend_schema(
        summary="Bind a new card", request=CardBindSerializer, responses=CardSerializer
    ),
    update=extend_schema(
        summary="Update a card (is_main, background_image)",
        parameters=[
            OpenApiParameter(name="pk", description="Card ID", required=True, type=int)
        ],
    ),
    partial_update=extend_schema(
        summary="Partially update a card (is_main, background_image)",
        parameters=[
            OpenApiParameter(name="pk", description="Card ID", required=True, type=int)
        ],
    ),
    destroy=extend_schema(
        summary="Delete card by ID",
        parameters=[
            OpenApiParameter(name="pk", description="Card ID", required=True, type=int)
        ],
    ),
)
class CardViewSet(viewsets.ModelViewSet):
    queryset = Card.objects.all()
    serializer_class = CardSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "put", "patch", "delete"]

    def get_queryset(self):
        """Returns cards belonging to the current user."""
        return Card.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        """Creates a session for adding a new card."""
        serializer = CardBindSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = MulticardService()
        result = service.bind_card(
            user=request.user,
            pinfl=serializer.validated_data.get("pinfl"),
            phone=serializer.validated_data.get("phone"),
        )

        if result["success"]:
            request.session["bind_session_id"] = result.get("session_id")
            return Response(result, status=status.HTTP_200_OK)
        return Response(result, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, pk=None, *args, **kwargs):
        """Updates is_main or background_image of a card."""
        try:
            card = self.get_queryset().get(id=pk)
        except Card.DoesNotExist:
            raise Http404("Card not found or you don't have permission to update it")

        serializer = self.get_serializer(card, data=request.data, partial=False)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    def partial_update(self, request, pk=None, *args, **kwargs):
        """Partially updates is_main or background_image of a card."""
        try:
            card = self.get_queryset().get(id=pk)
        except Card.DoesNotExist:
            raise Http404("Card not found or you don't have permission to update it")

        serializer = self.get_serializer(card, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    def list(self, request, *args, **kwargs):
        """Returns a list of all cards for the current user."""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def retrieve(self, request, pk=None, *args, **kwargs):
        """Returns details of a specific card based on ID."""
        try:
            card = self.get_queryset().get(id=pk)
        except Card.DoesNotExist:
            raise Http404("Card not found or you don't have permission to view it")
        serializer = self.get_serializer(card)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def destroy(self, request, pk=None, *args, **kwargs):
        """Deletes a card based on its ID."""
        try:
            card = self.get_queryset().get(id=pk)
        except Card.DoesNotExist:
            raise Http404("Card not found or you don't have permission to delete it")

        service = MulticardService()
        result = service.delete_card(user=request.user, card_token=card.card_token)

        if result["success"]:
            return Response(result, status=status.HTTP_204_NO_CONTENT)
        return Response(result, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["post"], permission_classes=[])
    def callback(self, request):
        """Processes the callback received from Multicard."""
        service = MulticardService()
        result = service.handle_callback(request.data)

        if result["success"]:
            return Response(result, status=status.HTTP_200_OK)
        return Response(result, status=status.HTTP_400_BAD_REQUEST)


@extend_schema_view(
    list=extend_schema(
        summary="List all balance status levels",
        description="Returns a paginated list of all balance status levels (bronze, silver, gold etc.)",
        parameters=[
            OpenApiParameter(
                name="search",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Search by name or description",
            ),
            OpenApiParameter(
                name="ordering",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Which field to use when ordering the results (minimum_amount, next_minimum_amount, percentage)",
            ),
        ],
    ),
    retrieve=extend_schema(
        summary="Retrieve a balance status level",
        description="Get detailed information about a specific balance status level",
    ),
    create=extend_schema(
        summary="Create a new balance status level",
        description="Admin only endpoint to create new balance status levels",
    ),
    update=extend_schema(
        summary="Update a balance status level",
        description="Admin only endpoint to fully update a balance status level",
    ),
    partial_update=extend_schema(
        summary="Partial update a balance status level",
        description="Admin only endpoint to partially update a balance status level",
    ),
    destroy=extend_schema(
        summary="Delete a balance status level",
        description="Admin only endpoint to delete a balance status level",
    ),
)
class BalanceStatusViewSet(ModelViewSet):
    queryset = BalanceStatus.objects.all()
    serializer_class = BalanceStatusSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["name", "description_uz", "description_ru", "description_en"]
    ordering_fields = ["minimum_amount", "next_minimum_amount", "percentage"]


@extend_schema_view(
    list=extend_schema(
        summary="Get user's balance",
        description="Returns the balance information for the currently authenticated user",
        parameters=[
            OpenApiParameter(
                name="balance_status",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Filter by balance status ID",
            ),
            OpenApiParameter(
                name="ordering",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Which field to use when ordering the results (balance, total_sales)",
            ),
        ],
    ),
    retrieve=extend_schema(
        summary="Retrieve balance details",
        description="Get detailed information about a specific balance record (only accessible to owner or admin)",
    ),
    create=extend_schema(
        summary="Create a new balance record",
        description="Admin only endpoint to create new balance records",
    ),
    update=extend_schema(
        summary="Update a balance record",
        description="Admin only endpoint to fully update a balance record",
    ),
    partial_update=extend_schema(
        summary="Partial update a balance record",
        description="Admin only endpoint to partially update a balance record",
    ),
    destroy=extend_schema(
        summary="Delete a balance record",
        description="Admin only endpoint to delete a balance record",
    ),
)
class BalanceViewSet(ModelViewSet):
    serializer_class = BalanceSerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["balance_status"]
    search_fields = ["unique_id"]
    ordering_fields = ["balance", "total_sales"]

    def get_queryset(self):
        return Balance.objects.filter(user=self.request.user)


@extend_schema_view(
    list=extend_schema(
        summary="List user's cashbacks",
        description="Returns a list of cashbacks for the currently authenticated user",
        parameters=[
            OpenApiParameter(
                name="status",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Filter by cashback status",
            ),
            OpenApiParameter(
                name="ordering",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Which field to use when ordering the results (created_at, amount, cashback)",
            ),
            OpenApiParameter(
                name="search",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Search by order ID",
            ),
        ],
        examples=[
            OpenApiExample(
                "Example response",
                value={
                    "count": 1,
                    "next": None,
                    "previous": None,
                    "results": [
                        {
                            "id": 1,
                            "order": 123,
                            "balance": {
                                "id": 1,
                                "user": 1,
                                "unique_id": "BAL-123",
                                "balance": 1000.00,
                                "total_sales": 5000.00,
                                "balance_status": {
                                    "id": 1,
                                    "name": "Gold",
                                    "percentage": 5.0,
                                    "minimum_amount": 1000.00,
                                    "next_minimum_amount": 5000.00,
                                    "num": 3,
                                    "time_line": "monthly",
                                    "description": "Gold status description",
                                },
                                "created_at": "2023-01-01T00:00:00Z",
                                "updated_at": "2023-01-01T00:00:00Z",
                            },
                            "amount": 100.00,
                            "status": "pending",
                            "percentage": 10.0,
                            "cashback": 10.00,
                            "created_at": "2023-01-01T00:00:00Z",
                            "updated_at": "2023-01-01T00:00:00Z",
                        }
                    ],
                },
            )
        ],
    ),
    retrieve=extend_schema(
        summary="Retrieve cashback details",
        description="Get detailed information about a specific cashback record (only accessible to owner or admin)",
    ),
    create=extend_schema(
        summary="Create a new cashback record",
        description="Admin only endpoint to create new cashback records",
    ),
    update=extend_schema(
        summary="Update a cashback record",
        description="Admin only endpoint to fully update a cashback record",
    ),
    partial_update=extend_schema(
        summary="Partial update a cashback record",
        description="Admin only endpoint to partially update a cashback record",
    ),
    destroy=extend_schema(
        summary="Delete a cashback record",
        description="Admin only endpoint to delete a cashback record",
    ),
)
class CashbackViewSet(ModelViewSet):
    serializer_class = CashbackSerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = CashbackFilter
    search_fields = ["order__id"]
    ordering_fields = ["created_at", "amount", "cashback"]

    def get_queryset(self):
        return Cashback.objects.filter(balance__user=self.request.user).order_by('-id')
