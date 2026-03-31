from rest_framework import serializers
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.viewsets import ModelViewSet

from app.models.edu_video import EduVideo


class EduVideoSerializer(serializers.ModelSerializer):
    class Meta:
        model = EduVideo
        fields = "__all__"
        
        
class EduVideoViewSet(ModelViewSet):
    queryset = EduVideo.objects.all()
    serializer_class = EduVideoSerializer
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["title", "description"]
    ordering_fields = ["created_at", "title"]

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [AllowAny()]
        return [IsAuthenticated()]