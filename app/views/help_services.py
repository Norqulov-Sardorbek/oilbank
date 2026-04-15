from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from app.serializers.help_services import HelpServiceSerializer,HelpServiceEmployeeSerializer
from app.models.help_services import HelpService, HelpServiceEmployee


class HelpServiceViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = HelpService.objects.all()
    serializer_class = HelpServiceSerializer
    

class HelpServiceEmployeeViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = HelpServiceEmployee.objects.all()
    serializer_class = HelpServiceEmployeeSerializer
