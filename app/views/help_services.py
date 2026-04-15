from rest_framework.response import Response
from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from app.serializers.help_services import HelpServiceSerializer,HelpServiceEmployeeSerializer
from app.models.help_services import HelpService, HelpServiceEmployee


class HelpServiceViewSet(viewsets.ModelViewSet):
    permission_classes = [AllowAny]
    queryset = HelpService.objects.all()
    serializer_class = HelpServiceSerializer
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["accept_language"] = self.request.headers.get("Accept-Language", "uz")
        return context
    

class HelpServiceEmployeeViewSet(viewsets.ModelViewSet):
    permission_classes = [AllowAny]
    queryset = HelpServiceEmployee.objects.all()
    serializer_class = HelpServiceEmployeeSerializer

class HelpServiceEmployeesAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, help_service_id):
        employees = HelpServiceEmployee.objects.filter(help_service_id=help_service_id)
        serializer = HelpServiceEmployeeSerializer(employees, many=True)
        return Response(serializer.data,status=200)
