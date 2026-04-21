from rest_framework import serializers
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.viewsets import ModelViewSet
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from app.models.edu_video import EduVideo,VideoCategory, VideoSubcategory

def get_request_language(request):
    lang = request.headers.get("Accept-Language", "uz").lower()

    if lang not in ["uz", "ru", "en"]:
        lang = "uz"

    return lang

class VideoCategorySerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    class Meta:
        model = VideoCategory
        fields = ["id", "name"]
        
    def get_name(self, obj):
        lang = get_request_language(self.context.get("request"))
        return getattr(obj, f"name_{lang}", obj.name_uz)

class VideoSubcategorySerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    class Meta:
        model = VideoSubcategory
        fields = ["id", "name"]
        
    def get_name(self, obj):
        lang = get_request_language(self.context.get("request"))
        return getattr(obj, f"name_{lang}", obj.name_uz)

class EduVideoSerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    class Meta:
        model = EduVideo
        fields = ["id", "category", "title", "description", "video_type", "video_url", "video_file", "file_size"]
    def get_title(self, obj):
        lang = get_request_language(self.context.get("request"))
        return getattr(obj, f"title_{lang}", obj.title_uz)
    def get_description(self, obj):
        lang = get_request_language(self.context.get("request"))
        return getattr(obj, f"description_{lang}", obj.description_uz)
        
        
class VideoCategoryViewSet(ModelViewSet):
    queryset = VideoCategory.objects.all()
    serializer_class = VideoCategorySerializer
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["name_uz", "name_ru", "name_en"]
    ordering_fields = ["id", "name_uz"]

class VideoSubcategoryViewSet(ModelViewSet):
    queryset = VideoSubcategory.objects.all()
    serializer_class = VideoSubcategorySerializer
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["name_uz", "name_ru", "name_en"]
    ordering_fields = ["id", "name_uz"]
    
    @swagger_auto_schema(
        operation_description="List all video subcategories or create a new one.",
        manual_parameters=[
            openapi.Parameter(
                "category_id",
                openapi.IN_QUERY,
                description="Filter subcategories by category ID",
                type=openapi.TYPE_INTEGER,
            )
        ],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
    def get_queryset(self):
        queryset = super().get_queryset()
        category_id = self.request.query_params.get("category_id")
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        return queryset
            

class EduVideoViewSet(ModelViewSet):
    queryset = EduVideo.objects.all()
    serializer_class = EduVideoSerializer
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["title", "description"]
    ordering_fields = ["created_at", "title"]

    
    @swagger_auto_schema(
        operation_description="List all educational videos or create a new one.",
        manual_parameters=[
            openapi.Parameter(
                "category_id",
                openapi.IN_QUERY,
                description="Filter videos by category ID",
                type=openapi.TYPE_INTEGER,
            )
        ],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [AllowAny()]
        return [IsAuthenticated()]
    def get_queryset(self):
        queryset = super().get_queryset()
        subcategory_id = self.request.query_params.get("subcategory_id")
        if subcategory_id:
            queryset = queryset.filter(category_id=subcategory_id)
        return queryset