# global imports
from geopy.distance import geodesic
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework.views import APIView
from drf_spectacular.types import OpenApiTypes
from rest_framework.response import Response
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
    OpenApiParameter,
    OpenApiExample,
)

from app.models.company_info import (
    FAQ,
    UserAgreement,
    PrivacyPolicy,
    Branch,
    Contact,
    SupportContact,
    Document,
    CompanyBenefit,
    CompanyComment,
    WebPageInfo, 
    StaticPage,
    LandingPageBanner,
)
from app.permissions import IsAdminOrReadOnly
from app.serializers.company_info import (
    FAQSerializer,
    UserAgreementSerializer,
    PrivacyPolicySerializer,
    BranchSerializer,
    ContactSerializer,
    SupportContactSerializer,
    DocumentOutputSerializer,
    DocumentInputSerializer,
    BranchListSerializer,
    FAQCreateUpdateSerializer,
    CompanyBenefitSerializer,
    CompanyCommentSerializer,
    WebPageInfoSerializer, 
    StaticPageSerializer, 
    StaticPageListSerializer, 
    RequestFormSerializer,
    LandingPageBannerSerializer,
)


@extend_schema_view(
    list=extend_schema(
        summary="List all branches",
        description="Returns a list of all branches with their details",
    ),
    retrieve=extend_schema(
        summary="Retrieve a branch",
        description="Returns detailed information about a specific branch",
    ),
    create=extend_schema(
        summary="Create a branch",
        description="Creates a new branch with the provided details",
    ),
    update=extend_schema(
        summary="Update a branch", description="Updates all fields of a branch"
    ),
    partial_update=extend_schema(
        summary="Partial update a branch",
        description="Updates selected fields of a branch",
    ),
    destroy=extend_schema(
        summary="Delete a branch", description="Deletes a specific branch"
    ),
)
class BranchViewSet(ModelViewSet):
    queryset = Branch.objects.filter(branch_type="REGULAR").order_by("name")
    permission_classes = [AllowAny]

    def get_serializer_class(self):
        if self.action == "nearest":
            return BranchListSerializer
        return BranchSerializer

    @extend_schema(
        methods=["GET", "POST"],
        summary="Get nearest branches by coordinates",
        description="Returns a list of nearest branches sorted by distance from the given latitude and longitude.",
        parameters=[
            OpenApiParameter(
                name="lat",
                required=True,
                type=float,
                location=OpenApiParameter.QUERY,
                description="User latitude",
            ),
            OpenApiParameter(
                name="lon",
                required=True,
                type=float,
                location=OpenApiParameter.QUERY,
                description="User longitude",
            ),
            OpenApiParameter(
                name="limit",
                required=False,
                type=int,
                location=OpenApiParameter.QUERY,
                description="Maximum number of branches to return (default is 5)",
            ),
        ],
        responses={200: BranchListSerializer(many=True)},
        examples=[
            OpenApiExample(
                "Example GET request",
                value={"lat": 41.3111, "lon": 69.2797, "limit": 3},
                request_only=True,
            )
        ],
    )
    @action(detail=False, methods=["get", "post"])
    def nearest(self, request):
        data = request.data if request.method == "POST" else request.query_params

        user_lat = data.get("lat")
        user_lon = data.get("lon")
        limit = int(data.get("limit", 5))

        if not user_lat or not user_lon:
            return Response(
                {"error": "latitude and longitude parameters are required"}, status=400
            )

        try:
            user_location = (float(user_lat), float(user_lon))
        except ValueError:
            return Response(
                {"error": "Invalid latitude or longitude values"}, status=400
            )

        branches_with_distance = []
        for branch in self.queryset.exclude(latitude__isnull=True).exclude(
            longitude__isnull=True
        ):
            try:
                branch_location = (float(branch.latitude), float(branch.longitude))
                distance = geodesic(user_location, branch_location).km
                branches_with_distance.append({"branch": branch, "distance": distance})
            except (TypeError, ValueError):
                continue

        sorted_branches = sorted(branches_with_distance, key=lambda x: x["distance"])[
            :limit
        ]

        distance_map = {
            item["branch"].id: round(item["distance"], 2) for item in sorted_branches
        }

        serializer = self.get_serializer(
            [item["branch"] for item in sorted_branches],
            many=True,
            context={"distance_map": distance_map, "request": request},
        )

        return Response(serializer.data)


@extend_schema_view(
    list=extend_schema(
        summary="List all FAQs (Management)",
        description="Returns all FAQs for management purposes",
    ),
    create=extend_schema(
        summary="Create a new FAQ", description="Adds a new frequently asked question"
    ),
    retrieve=extend_schema(
        summary="Retrieve an FAQ", description="Returns details of a specific FAQ"
    ),
    update=extend_schema(
        summary="Update an FAQ", description="Modifies all fields of an FAQ"
    ),
    partial_update=extend_schema(
        summary="Partial update an FAQ",
        description="Modifies selected fields of an FAQ",
    ),
    destroy=extend_schema(
        summary="Delete an FAQ", description="Removes an FAQ from the system"
    ),
)
class FAQManageView(ModelViewSet):
    queryset = FAQ.objects.all().order_by("order_number")
    serializer_class = FAQSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_serializer_class(self):
        if self.action in ["list", "retrieve"]:
            return FAQSerializer
        return FAQCreateUpdateSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context


@extend_schema(
    summary="Get User Agreement",
    description="Returns the current user agreement text",
    responses={200: UserAgreementSerializer},
)
class UserAgreementListView(ListAPIView):
    queryset = UserAgreement.objects.all()
    serializer_class = UserAgreementSerializer
    permission_classes = [AllowAny]


@extend_schema(
    summary="Get Privacy Policy",
    description="Returns the current privacy policy text",
    responses={200: PrivacyPolicySerializer},
)
class PrivacyPolicyListView(ListAPIView):
    queryset = PrivacyPolicy.objects.all()
    serializer_class = PrivacyPolicySerializer
    permission_classes = [AllowAny]


@extend_schema(
    summary="Get Documents",
    description="Returns the current documents",
    responses={200: DocumentOutputSerializer},
)
class DocumentViewSet(ModelViewSet):
    queryset = Document.objects.all()
    permission_classes = [IsAdminOrReadOnly]

    def get_serializer_class(self):
        if self.request.method in ["GET", "HEAD"]:
            return DocumentOutputSerializer
        return DocumentInputSerializer


@extend_schema_view(
    list=extend_schema(
        summary="List all Contacts",
        description="Returns all contacts for management or display purposes",
    ),
    create=extend_schema(
        summary="Create a new Contact", description="Adds a new contact to the system"
    ),
    retrieve=extend_schema(
        summary="Retrieve a Contact",
        description="Returns details of a specific contact",
    ),
    update=extend_schema(
        summary="Update a Contact",
        description="Modifies all fields of a specific contact",
    ),
    partial_update=extend_schema(
        summary="Partial update a Contact",
        description="Modifies selected fields of a specific contact",
    ),
    destroy=extend_schema(
        summary="Delete a Contact", description="Removes a contact from the system"
    ),
)
class ContactViewSet(ModelViewSet):
    queryset = Contact.objects.all()
    serializer_class = ContactSerializer
    permission_classes = [AllowAny]


class CombinedSupportInfoView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        faqs = FAQ.objects.all().order_by("order_number")
        support_contact = SupportContact.objects.first()

        faq_data = FAQSerializer(faqs, many=True).data
        support_data = (
            SupportContactSerializer(support_contact).data if support_contact else {}
        )

        response_data = {"faq": faq_data, "support": support_data}

        return Response(response_data)


@extend_schema_view(
    list=extend_schema(
        summary="List all content items",
        description="Returns a list of all content items with titles and descriptions in the language specified by the Accept-Language header (en, ru, uz).",
        responses={
            200: CompanyBenefitSerializer(many=True),
        },
        examples=[
            OpenApiExample(
                "List content (English)",
                value=[
                    {
                        "id": 1,
                        "image": "/media/content/image1.jpg",
                        "title": "Sample Title",
                        "description": "Sample Description",
                        "created_at": "2025-05-23T17:54:00Z",
                        "updated_at": "2025-05-23T17:54:00Z",
                    },
                    {
                        "id": 2,
                        "image": "/media/content/image2.jpg",
                        "title": "Another Title",
                        "description": "Another Description",
                        "created_at": "2025-05-23T18:00:00Z",
                        "updated_at": "2025-05-23T18:00:00Z",
                    },
                ],
                request_only=False,
                response_only=True,
            )
        ],
    ),
    retrieve=extend_schema(
        summary="Retrieve a content item",
        description="Returns detailed information about a specific content item in the language specified by the Accept-Language header (en, ru, uz).",
        responses={200: CompanyBenefitSerializer, 404: None},
        examples=[
            OpenApiExample(
                "Retrieve content (Russian)",
                value={
                    "id": 1,
                    "image": "/media/content/image1.jpg",
                    "title": "Пример заголовка",
                    "description": "Пример описания",
                    "created_at": "2025-05-23T17:54:00Z",
                    "updated_at": "2025-05-23T17:54:00Z",
                },
                request_only=False,
                response_only=True,
            )
        ],
    ),
    create=extend_schema(
        summary="Create a content item",
        description="Creates a new content item with an optional image and titles/descriptions in English, Russian, and Uzbek.",
        request=CompanyBenefitSerializer,
        responses={201: CompanyBenefitSerializer, 400: None},
        examples=[
            OpenApiExample(
                "Create content request",
                value={
                    "image": "image.jpg",
                    "title_en": "Sample Title",
                    "description_en": "Sample Description",
                    "title_ru": "Пример заголовка",
                    "description_ru": "Пример описания",
                    "title_uz": "Namuna Sarlavha",
                    "description_uz": "Namuna Tavsifi",
                },
                request_only=True,
                response_only=False,
            )
        ],
    ),
    update=extend_schema(
        summary="Update a content item",
        description="Updates all fields of a specific content item, including image and multilingual titles/descriptions.",
        request=CompanyBenefitSerializer,
        responses={200: CompanyBenefitSerializer, 400: None, 404: None},
        examples=[
            OpenApiExample(
                "Update content request",
                value={
                    "image": "updated_image.jpg",
                    "title_en": "Updated Title",
                    "description_en": "Updated Description",
                    "title_ru": "Обновленный заголовок",
                    "description_ru": "Обновленное описание",
                    "title_uz": "Yangilangan Sarlavha",
                    "description_uz": "Yangilangan Tavsifi",
                },
                request_only=True,
                response_only=False,
            )
        ],
    ),
    partial_update=extend_schema(
        summary="Partial update a content item",
        description="Updates selected fields of a specific content item, such as image or specific language titles/descriptions.",
        request=CompanyBenefitSerializer,
        responses={200: CompanyBenefitSerializer, 400: None, 404: None},
        examples=[
            OpenApiExample(
                "Partial update content request",
                value={
                    "title_en": "Partially Updated Title",
                    "description_ru": "Частично обновленное описание",
                },
                request_only=True,
                response_only=False,
            )
        ],
    ),
    destroy=extend_schema(
        summary="Delete a content item",
        description="Deletes a specific content item by ID.",
        responses={204: None, 404: None},
    ),
)
class ContentViewSet(ModelViewSet):
    queryset = CompanyBenefit.objects.all()
    serializer_class = CompanyBenefitSerializer
    permission_classes = [AllowAny]


@extend_schema_view(
    list=extend_schema(
        summary="List all content items",
        description="Returns a list of all content items with titles and descriptions in the language specified by the Accept-Language header (en, ru, uz).",
        responses={
            200: CompanyBenefitSerializer(many=True),
        },
        examples=[
            OpenApiExample(
                "List content (English)",
                value=[
                    {
                        "id": 1,
                        "image": "/media/content/image1.jpg",
                        "title": "Sample Title",
                        "description": "Sample Description",
                        "created_at": "2025-05-23T17:54:00Z",
                        "updated_at": "2025-05-23T17:54:00Z",
                    },
                    {
                        "id": 2,
                        "image": "/media/content/image2.jpg",
                        "title": "Another Title",
                        "description": "Another Description",
                        "created_at": "2025-05-23T18:00:00Z",
                        "updated_at": "2025-05-23T18:00:00Z",
                    },
                ],
                request_only=False,
                response_only=True,
            )
        ],
    ),
    retrieve=extend_schema(
        summary="Retrieve a content item",
        description="Returns detailed information about a specific content item in the language specified by the Accept-Language header (en, ru, uz).",
        responses={200: CompanyBenefitSerializer, 404: OpenApiTypes.NONE},
        examples=[
            OpenApiExample(
                "Retrieve content (Russian)",
                value={
                    "id": 1,
                    "image": "/media/content/image1.jpg",
                    "title": "Пример заголовка",
                    "description": "Пример описания",
                    "created_at": "2025-05-23T17:54:00Z",
                    "updated_at": "2025-05-23T17:54:00Z",
                },
                request_only=False,
                response_only=True,
            )
        ],
    ),
    create=extend_schema(
        summary="Create a content item",
        description="Creates a new content item with an optional image and titles/descriptions in English, Russian, and Uzbek.",
        request=CompanyBenefitSerializer,
        responses={201: CompanyBenefitSerializer, 400: OpenApiTypes.NONE},
        examples=[
            OpenApiExample(
                "Create content request",
                value={
                    "image": "image.jpg",
                    "title_en": "Sample Title",
                    "description_en": "Sample Description",
                    "title_ru": "Пример заголовка",
                    "description_ru": "Пример описания",
                    "title_uz": "Namuna Sarlavha",
                    "description_uz": "Namuna Tavsifi",
                },
                request_only=True,
                response_only=False,
            )
        ],
    ),
    update=extend_schema(
        summary="Update a content item",
        description="Updates all fields of a specific content item, including image and multilingual titles/descriptions.",
        request=CompanyBenefitSerializer,
        responses={
            200: CompanyBenefitSerializer,
            400: OpenApiTypes.NONE,
            404: OpenApiTypes.NONE,
        },
        examples=[
            OpenApiExample(
                "Update content request",
                value={
                    "image": "updated_image.jpg",
                    "title_en": "Updated Title",
                    "description_en": "Updated Description",
                    "title_ru": "Обновленный заголовок",
                    "description_ru": "Обновленное описание",
                    "title_uz": "Yangilangan Sarlavha",
                    "description_uz": "Yangilangan Tavsifi",
                },
                request_only=True,
                response_only=False,
            )
        ],
    ),
    partial_update=extend_schema(
        summary="Partial update a content item",
        description="Updates selected fields of a specific content item, such as image or specific language titles/descriptions.",
        request=CompanyBenefitSerializer,
        responses={
            200: CompanyBenefitSerializer,
            400: OpenApiTypes.NONE,
            404: OpenApiTypes.NONE,
        },
        examples=[
            OpenApiExample(
                "Partial update content request",
                value={
                    "title_en": "Partially Updated Title",
                    "description_ru": "Частично обновленное описание",
                },
                request_only=True,
                response_only=False,
            )
        ],
    ),
    destroy=extend_schema(
        summary="Delete a content item",
        description="Deletes a specific content item by ID.",
        responses={204: OpenApiTypes.NONE, 404: OpenApiTypes.NONE},
    ),
)
class CompanyCommentViewSet(ModelViewSet):
    queryset = CompanyComment.objects.all()
    serializer_class = CompanyCommentSerializer
    permission_classes = [AllowAny]


class WebPageInfoViewSet(ModelViewSet):
    """
    ViewSet for managing web page information.
    """

    queryset = WebPageInfo.objects.all()
    serializer_class = WebPageInfoSerializer
    permission_classes = [AllowAny]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context


@extend_schema(
    summary="Retrieve a static page",
    description="Returns detailed information about a specific static page in the language specified by the Accept-Language header (en, ru, uz).",
    responses={200: StaticPageSerializer, 404: OpenApiTypes.NONE},
    examples=[
        OpenApiExample(
            "Retrieve static page (Russian)",
            value={
                "id": 1,
                "title": "Пример заголовка",
                "content": "Пример контента",
                "created_at": "2025-05-23T17:54:00Z",
                "updated_at": "2025-05-23T17:54:00Z",
            },
            request_only=False,
            response_only=True,
        )
    ],
)
class StaticPageViewSet(ReadOnlyModelViewSet):
    queryset = StaticPage.objects.all()
    serializer_class = StaticPageSerializer
    permission_classes = [AllowAny]
    http_method_names = ["get"]
    lookup_field = 'slug'

    def get_serializer_class(self):
        if self.action == 'list':
            return StaticPageListSerializer
        return super().get_serializer_class()

@extend_schema(
    summary="Submit a request form",
    description="Allows users to submit a request form from a static page (e.g., About page). The source_page is the slug of the StaticPage. All fields except email and source_page are required.",
    operation_id="create_request_form",
    request=RequestFormSerializer,
    responses={
        201: RequestFormSerializer,
        400: OpenApiTypes.OBJECT,
    },
    examples=[
        OpenApiExample(
            "Submit request form",
            value={
                "name": "John",
                "surname": "Doe",
                "organization": "Carland Inc.",
                "phone": "+998901234567",
                "email": "john.doe@example.com",
                "source_page": "carland-oil-change",
            },
            request_only=True,
            response_only=False,
        ),
        OpenApiExample(
            "Successful response",
            value={
                "id": 1,
                "name": "John",
                "surname": "Doe",
                "organization": "Carland Inc.",
                "phone": "+998901234567",
                "email": "john.doe@example.com",
                "source_page": "carland-oil-change",
                "created_at": "2025-07-07T18:50:00Z",
            },
            request_only=False,
            response_only=True,
        ),
        OpenApiExample(
            "Error response",
            value={
                "name": ["This field is required."],
                "surname": ["This field is required."],
                "organization": ["This field is required."],
                "phone": ["This field is required."],
            },
            request_only=False,
            response_only=True,
            status_codes=["400"],
        ),
    ],
)
class RequestFormCreateView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        serializer = RequestFormSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LandingPageBannerListAPIView(ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = LandingPageBannerSerializer
    pagination_class = None  # return all banners
    queryset = LandingPageBanner.objects.all().order_by("order_number", "id")