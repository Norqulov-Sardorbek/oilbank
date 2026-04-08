from rest_framework import status, viewsets
from rest_framework.response import Response

from app.models.qr_codes import QRCode
from app.serializers.qr_codes import QRCodeSerializer


class QRCodeViewSet(viewsets.ModelViewSet):
    queryset = QRCode.objects.all()
    serializer_class = QRCodeSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        qr_codes = serializer.save()

        response_serializer = self.get_serializer(qr_codes, many=True)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)