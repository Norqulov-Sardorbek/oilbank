import uuid
from io import BytesIO

import qrcode
from django.core.files.base import ContentFile
from rest_framework import serializers
from qrcode.constants import ERROR_CORRECT_H
from PIL import Image

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
        url = f"https://carland.upgrow.uz/user/qr/{unique_code}"
        qr = qrcode.QRCode(
        version=None,
        error_correction=ERROR_CORRECT_H,
        box_size=10,
        border=1,
    )
        qr.add_data(url)
        qr.make(fit=True)

        qr_img = qr.make_image(
            fill_color="black",
            back_color="white"
        ).convert("RGBA")

        # 2. Frame (ramka) ni ochamiz
        frame = Image.open("utils/Carland_Sticker_Glass_V1_Монтажная область 1.tif").convert("RGBA")
        # 🔁 o‘zingni path qo‘y: masalan media yoki static

        # 3. QR size ni framega moslab kichraytiramiz
        frame_w, frame_h = frame.size

        qr_size = int(frame_w * 0.6)  # QR frame ichida 50% bo‘lsin
        qr_img = qr_img.resize((qr_size, qr_size))

        # 4. O‘rtaga joylaymiz
        pos = (
            (frame_w - qr_size) // 2+8,
            (frame_h - qr_size) // 2-130,
        )

        # 5. QR ni frame ustiga qo‘yish
        frame.paste(qr_img, pos, qr_img)

        # 6. Saqlash
        
        buffer = BytesIO()
        
        frame.save(buffer, format="PNG")
        filename = f"{unique_code}.png"
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