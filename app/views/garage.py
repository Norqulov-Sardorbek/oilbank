from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.viewsets import ModelViewSet

from app.custom_filters import CarFilter
from app.models.garage import (
    Car,
    OilChangedHistory,
    CarModel,
    Firm,
    CarColor,
    OilChangeRating,
)
from app.serializers.garage import (
    CarCreateSerializer,
    CarUpdateSerializer,
    CarListSerializer,
    OilChangedHistorySerializer,
    CarModelSerializer,
    FirmSerializer,
    CarColorSerializer,
    OilChangeRatingSerializer,
)
from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
    OpenApiParameter,
    OpenApiExample,
)
from drf_spectacular.types import OpenApiTypes
from django.utils.translation import gettext as _
from rest_framework.response import Response
from rest_framework import status



@extend_schema_view(
    list=extend_schema(
        summary="List user's Oil change ratings",
        description="Returns a list of all Oil change ratings made by the authenticated user.",
        responses={200: OilChangeRatingSerializer(many=True)},
    ),
    create=extend_schema(
        summary="Rate an Oil change",
        description="Allows an authenticated user to rate an Oil change they have received.",
        request=OilChangeRatingSerializer,
        responses={
            201: OilChangeRatingSerializer,
            400: {"detail": "Invalid data or already rated"},
        },
    ),
)
class OilChangeRatingViewSet(ModelViewSet):
    queryset = OilChangeRating.objects.all()
    serializer_class = OilChangeRatingSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "delete"]

    def get_queryset(self):
        return self.queryset.filter(reviewer=self.request.user)

    def create(self, request, *args, **kwargs):
        super().create(request, *args, **kwargs)
        return Response({"message": _("Oil change has been rated")}, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        super().destroy(request, *args, **kwargs)
        return Response({"message": _("Oil change rating deleted successfully")}, status=status.HTTP_204_NO_CONTENT)


@extend_schema_view(
    list=extend_schema(
        summary="List Cars",
        description="Return a list of cars filtered by the authenticated user with optional filters.",
        parameters=[
            OpenApiParameter(
                name="created_at__gte",
                required=False,
                type={"format": "date-time"},
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name="created_at__lte",
                required=False,
                type={"format": "date-time"},
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name="updated_at__gte",
                required=False,
                type={"format": "date-time"},
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name="updated_at__lte",
                required=False,
                type={"format": "date-time"},
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name="firm", required=False, type=int, location=OpenApiParameter.QUERY
            ),
            OpenApiParameter(
                name="firm_name",
                required=False,
                type=str,
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name="model", required=False, type=int, location=OpenApiParameter.QUERY
            ),
            OpenApiParameter(
                name="model_name",
                required=False,
                type=str,
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name="number", required=False, type=str, location=OpenApiParameter.QUERY
            ),
        ],
    ),
    retrieve=extend_schema(
        summary="Retrieve a car",
        description="Returns detailed information about a specific car belonging to the user",
        responses={200: CarListSerializer},
    ),
    create=extend_schema(
        summary="Create a new car",
        description="Adds a new car for the authenticated user",
        request=CarCreateSerializer,
        responses={201: CarListSerializer},
    ),
    update=extend_schema(
        summary="Update a car",
        description="Updates all fields of a car (must belong to user)",
        request=CarUpdateSerializer,
        responses={200: CarListSerializer},
    ),
    partial_update=extend_schema(
        summary="Partial update a car",
        description="Updates selected fields of a car (must belong to user)",
        request=CarUpdateSerializer,
        responses={200: CarListSerializer},
    ),
    destroy=extend_schema(
        summary="Delete a car",
        description="Removes a car from the user's garage",
        responses={204: None},
    ),
)
class CarViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    filterset_class = CarFilter
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ["created_at", "updated_at"]

    def get_queryset(self):
        return (
            Car.objects.select_related("user", "firm", "model")
            .prefetch_related("oil_change_history")
            .filter(user=self.request.user)
        )

    def get_serializer_class(self):
        if self.request.method == "POST":
            return CarCreateSerializer
        elif self.request.method in ["PUT", "PATCH"]:
            return CarUpdateSerializer
        return CarListSerializer

    def retrieve(self, request, *args, **kwargs):
        response = super().retrieve(request, *args, **kwargs)
        instance = self.get_object()
        return Response(
            {
                "message": _("Car retrieved successfully"),
                "data": CarListSerializer(instance, context={"request": request}).data,
            },
            status=status.HTTP_200_OK,
        )

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        return Response(
            {"message": _("Car created successfully"), "data": response.data},
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        return Response(
            {
                "message": _("Car updated successfully"),
                "data": CarListSerializer(
                    self.get_object(), context={"request": request}
                ).data,
            },
            status=status.HTTP_200_OK,
        )

    def partial_update(self, request, *args, **kwargs):
        response = super().partial_update(request, *args, **kwargs)
        return Response(
            {
                "message": _("Car partially updated successfully"),
                "data": CarListSerializer(
                    self.get_object(), context={"request": request}
                ).data,
            },
            status=status.HTTP_200_OK,
        )

    def destroy(self, request, *args, **kwargs):
        super().destroy(request, *args, **kwargs)
        return Response(
            {"message": _("Oil change history deleted successfully.")},
            status=status.HTTP_204_NO_CONTENT,
        )


class CarColorViewSet(viewsets.ModelViewSet):
    queryset = CarColor.objects.all()
    serializer_class = CarColorSerializer
    http_method_names = ["get"]

    @extend_schema(
        summary="Get list of car colors",
        description="Retrieve a list of available car colors. You can optionally filter by `car_model_id`.",
        parameters=[
            OpenApiParameter(
                name="car_model_id",
                description="Filter by car model ID",
                required=False,
                type=int,
                location=OpenApiParameter.QUERY,
            ),
        ],
        responses={200: CarColorSerializer(many=True)},
        tags=["Car Colors"],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        car_model_id = self.request.query_params.get("car_model_id")
        if car_model_id is not None:
            return CarColor.objects.filter(car_model_id=car_model_id)
        return CarColor.objects.all()


@extend_schema_view(
    list=extend_schema(
        summary="List oil change history",
        description="Returns oil change history filtered by car_id query parameter",
        parameters=[
            OpenApiParameter(
                name="car_id",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Filter oil changes by car ID",
                required=False,
            ),
            OpenApiParameter(
                name="branch_id",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Filter oil changes by branch ID",
                required=False,
            ),
            OpenApiParameter(
                name="start_date",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description="Filter oil changes by start date",
                required=False,
            ),
            OpenApiParameter(
                name="end_date",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description="Filter oil changes by end date",
                required=False,
            ),
        ],
        responses={200: OilChangedHistorySerializer(many=True)},
    ),
    retrieve=extend_schema(
        summary="Retrieve oil change record",
        description="Returns detailed information about a specific oil change record",
        responses={200: OilChangedHistorySerializer},
    ),
    create=extend_schema(
        summary="Add oil change record",
        description="Adds a new oil change record (car must belong to user)",
        request=OilChangedHistorySerializer,
        responses={201: OilChangedHistorySerializer},
        examples=[
            OpenApiExample(
                "Example request",
                value={
                    "car": 1,
                    "changed_date": "2023-01-15",
                    "next_change_km": 15000,
                    "note": "Used synthetic oil",
                },
                request_only=True,
            )
        ],
    ),
    update=extend_schema(
        summary="Update oil change record",
        description="Updates all fields of an oil change record",
        request=OilChangedHistorySerializer,
        responses={200: OilChangedHistorySerializer},
    ),
    partial_update=extend_schema(
        summary="Partial update oil change record",
        description="Updates selected fields of an oil change record",
        request=OilChangedHistorySerializer,
        responses={200: OilChangedHistorySerializer},
    ),
    destroy=extend_schema(
        summary="Delete oil change record",
        description="Removes an oil change history record",
        responses={204: None},
    ),
)
class OilChangedHistoryViewSet(viewsets.ModelViewSet):
    serializer_class = OilChangedHistorySerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "put", "patch", "delete"]
    ordering = ["-id"]

    def get_queryset(self):
        user = self.request.user
        queryset = OilChangedHistory.objects.filter(car__user=user).order_by("-id")

        car_id = self.request.query_params.get("car_id")
        if car_id:
            queryset = queryset.filter(car_id=car_id)

        branch_id = self.request.query_params.get("branch_id")
        if branch_id:
            queryset = queryset.filter(branch_id=branch_id)

        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")

        if start_date and end_date:
            queryset = queryset.filter(
                created_at__date__gte=start_date, created_at__date__lte=end_date
            )
        elif start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        elif end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)

        return queryset

    def perform_create(self, serializer):
        car = serializer.validated_data.get("car")
        serializer.validated_data["source"] = OilChangedHistory.SourceChoices.OTHER
        user = self.request.user
        if car.user != user:
            raise PermissionDenied(
                _("You can only add oil change history for your own cars.")
            )
        serializer.save()

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        return Response(
            {
                "message": _("Oil change history added successfully."),
                "data": response.data,
            },
            status=status.HTTP_201_CREATED,
        )

    def retrieve(self, request, *args, **kwargs):
        response = super().retrieve(request, *args, **kwargs)
        return Response(
            {
                "message": _("Oil change history retrieved successfully."),
                "data": response.data,
            },
            status=status.HTTP_200_OK,
        )

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        return Response(
            {
                "message": _("Oil change history updated successfully."),
                "data": response.data,
            },
            status=status.HTTP_200_OK,
        )

    def partial_update(self, request, *args, **kwargs):
        response = super().partial_update(request, *args, **kwargs)
        return Response(
            {
                "message": _("Oil change history partially updated successfully."),
                "data": response.data,
            },
            status=status.HTTP_200_OK,
        )

    def destroy(self, request, *args, **kwargs):
        super().destroy(request, *args, **kwargs)
        return Response(
            {"message": _("Oil change history deleted successfully.")},
            status=status.HTTP_204_NO_CONTENT,
        )


@extend_schema_view(
    list=extend_schema(
        summary="List car models",
        description="Returns a list of all available car models",
        responses={200: CarModelSerializer(many=True)},
    ),
    retrieve=extend_schema(
        summary="Retrieve car model",
        description="Returns detailed information about a specific car model",
        responses={200: CarModelSerializer},
    ),
    create=extend_schema(
        summary="Create car model",
        description="Adds a new car model (admin only)",
        request=CarModelSerializer,
        responses={201: CarModelSerializer},
    ),
    update=extend_schema(
        summary="Update car model",
        description="Updates all fields of a car model (admin only)",
        request=CarModelSerializer,
        responses={200: CarModelSerializer},
    ),
    partial_update=extend_schema(
        summary="Partial update car model",
        description="Updates selected fields of a car model (admin only)",
        request=CarModelSerializer,
        responses={200: CarModelSerializer},
    ),
    destroy=extend_schema(
        summary="Delete car model",
        description="Removes a car model (admin only)",
        responses={204: None},
    ),
)
class CarModelViewSet(ModelViewSet):
    serializer_class = CarModelSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = CarModel.objects.all()
        firm_id = self.request.query_params.get("firm")

        if firm_id is not None:
            queryset = queryset.filter(firm_id=firm_id)

        return queryset


@extend_schema_view(
    list=extend_schema(
        summary="List firms",
        description="Returns a list of all available firms",
        responses={200: FirmSerializer(many=True)},
    ),
    retrieve=extend_schema(
        summary="Retrieve firm",
        description="Returns detailed information about a specific firm",
        responses={200: FirmSerializer},
    ),
    create=extend_schema(
        summary="Create firm",
        description="Adds a new firm (admin only)",
        request=FirmSerializer,
        responses={201: FirmSerializer},
    ),
    update=extend_schema(
        summary="Update firm",
        description="Updates all fields of a firm (admin only)",
        request=FirmSerializer,
        responses={200: FirmSerializer},
    ),
    partial_update=extend_schema(
        summary="Partial update firm",
        description="Updates selected fields of a firm (admin only)",
        request=FirmSerializer,
        responses={200: FirmSerializer},
    ),
    destroy=extend_schema(
        summary="Delete firm",
        description="Removes a firm (admin only)",
        responses={204: None},
    ),
)
class FirmViewSet(ModelViewSet):
    queryset = Firm.objects.all()
    serializer_class = FirmSerializer
    permission_classes = [AllowAny]
