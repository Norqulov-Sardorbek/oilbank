from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from app.serializers.help_services import HelpServiceSerializer,HelpServiceEmployeeSerializer
from app.models.help_services import HelpService, HelpServiceEmployee


class HelpServiceViewSet(viewsets.ModelViewSet):
    permission_classes = [AllowAny]
    queryset = HelpService.objects.all()
    serializer_class = HelpServiceSerializer
    

class HelpServiceEmployeeViewSet(viewsets.ModelViewSet):
    permission_classes = [  AllowAny]
    queryset = HelpServiceEmployee.objects.all()
    serializer_class = HelpServiceEmployeeSerializer
