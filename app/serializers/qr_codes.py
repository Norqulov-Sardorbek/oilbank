import uuid
from io import BytesIO

import qrcode
from django.core.files.base import ContentFile
from rest_framework import serializers

from app.models.qr_codes import QRCode


class QRCodeSerializer(serializers.ModelSerializer):
    quantity = serializers.IntegerField(write_only=True, required=False, min_value=1)

    class Meta:
        model = QRCode
        fields = ['id', 'unique_code', 'image', 'quantity']
        read_only_fields = ['id', 'unique_code', 'image']

    def generate_unique_code(self) -> str:
        while True:
            code = uuid.uuid4().hex[:12].upper()
            if not QRCode.objects.filter(unique_code=code).exists():
                return code

    def generate_qr_image(self, unique_code: str) -> ContentFile:
        qr = qrcode.make(unique_code)

        buffer = BytesIO()
        qr.save(buffer, format='PNG')

        filename = f'{unique_code}.png'
        return ContentFile(buffer.getvalue(), name=filename)

    def create(self, validated_data):
        quantity = validated_data.pop('quantity', 1)

        qr_codes = []
        for _ in range(quantity):
            unique_code = self.generate_unique_code()
            qr_image = self.generate_qr_image(unique_code)

            qr_code = QRCode.objects.create(
                unique_code=unique_code,
                image=qr_image,
            )
            qr_codes.append(qr_code)

        return qr_codes