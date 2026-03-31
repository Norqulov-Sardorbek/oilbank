from django.shortcuts import get_object_or_404
import base64
import logging
import uuid
from django.core.files.base import ContentFile
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

logger = logging.getLogger(__name__)


class BaseOdooIDSerializer(serializers.ModelSerializer):

    def validate(self, attrs):
        odoo_id = attrs.get("odoo_id")

        if not odoo_id:
            raise ValidationError({"odoo_id": "This field is required."})

        model = self.Meta.model
        queryset = model.objects.filter(odoo_id=odoo_id)

        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise ValidationError({"odoo_id": "This odoo_id must be unique."})

        return attrs

    def get_related_object(self, model, identifier):
        # identifier: str (odoo_id) yoki model instance bo‘lishi mumkin
        odoo_id = getattr(identifier, "odoo_id", identifier)
        return get_object_or_404(model, odoo_id=odoo_id)

    def create(self, validated_data):
        m2m_data = {}

        # ForeignKey va ManyToMany ma’lumotlarni ajratib olamiz
        for field_name, field in self.fields.items():
            if isinstance(field, serializers.SlugRelatedField) and not getattr(
                field, "many", False
            ):
                related_data = validated_data.get(field_name)
                if related_data is not None:
                    model = field.queryset.model
                    validated_data[field_name] = self.get_related_object(
                        model, related_data
                    )
            elif getattr(field, "many", False) and isinstance(
                field.child_relation, serializers.SlugRelatedField
            ):
                m2m_data[field_name] = validated_data.pop(field_name, [])

        # Asosiy model instance yaratamiz (ManyToManysiz)
        instance = super().create(validated_data)

        # ManyToMany maydonlarni alohida o‘rnatamiz
        for field_name, values in m2m_data.items():
            model = self.fields[field_name].child_relation.queryset.model
            related_objects = [self.get_related_object(model, val) for val in values]
            getattr(instance, field_name).set(related_objects)

        return instance

    def update(self, instance, validated_data):
        m2m_data = {}

        # ForeignKey va ManyToMany maydonlarni alohida ajratamiz
        for field_name, field in self.fields.items():
            if isinstance(field, serializers.SlugRelatedField) and not getattr(
                field, "many", False
            ):
                related_data = validated_data.pop(field_name, None)
                if related_data is not None:
                    model = field.queryset.model
                    setattr(
                        instance,
                        field_name,
                        self.get_related_object(model, related_data),
                    )
                else:
                    setattr(instance, field_name, None)
            elif getattr(field, "many", False) and isinstance(
                field.child_relation, serializers.SlugRelatedField
            ):
                m2m_data[field_name] = validated_data.pop(field_name, [])

        # Oddiy maydonlarni yangilash (ManyToMany maydonlar bundan tashqari)
        for attr, value in validated_data.items():
            field = self.Meta.model._meta.get_field(attr)
            if not field.many_to_many:
                setattr(instance, attr, value)
            else:
                # Agar kutilmagan holat bo‘lsa, M2M uchun ajratib qo‘yamiz
                m2m_data[attr] = value

        instance.save()

        # ManyToMany maydonlarni yangilash
        for field_name, values in m2m_data.items():
            model = self.fields[field_name].child_relation.queryset.model
            related_objects = [self.get_related_object(model, val) for val in values]
            getattr(instance, field_name).set(related_objects)

        return instance


class Base64ImageField(serializers.ImageField):
    """
    ImageField that handles base64-encoded images with better error handling.
    """

    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith("data:image"):
            try:
                # Split format and base64 data
                format_str, img_str = data.split(";base64,")
                ext = format_str.split("/")[-1]

                # Decode base64 data
                file_data = base64.b64decode(img_str)

                # Validate that we have actual data
                if not file_data or len(file_data) == 0:
                    logger.error("Decoded image data is empty")
                    raise ValidationError("The uploaded image data is empty or corrupted.")

                # Create ContentFile with proper extension
                file_name = f"{uuid.uuid4().hex[:10]}.{ext}"
                data = ContentFile(file_data, name=file_name)

            except base64.binascii.Error as e:
                logger.error(f"Base64 decode error: {e}")
                raise ValidationError("Invalid base64 encoding in image data.")
            except ValueError as e:
                logger.error(f"Image data format error: {e}")
                raise ValidationError("Invalid image data format. Expected 'data:image/<type>;base64,<data>'.")
            except Exception as e:
                logger.error(f"Unexpected error processing image: {e}")
                raise ValidationError(f"Failed to process image: {str(e)}")

        # Pass to parent ImageField for PIL validation
        try:
            return super().to_internal_value(data)
        except Exception as e:
            logger.error(f"Image validation failed: {e}")
            raise ValidationError(f"Upload a valid image. The file you uploaded was either not an image or a corrupted image. Details: {str(e)}")


class Base64FileField(serializers.FileField):
    """
    FileField that handles base64-encoded files (e.g., video, audio, docs).
    """

    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith("data:"):
            try:
                # "data:video/mp4;base64,AAAA..."
                format_str, file_str = data.split(";base64,")
                mime_type = format_str.split(":")[1]   # e.g., "video/mp4"
                ext = mime_type.split("/")[-1]        # "mp4"
                file_data = base64.b64decode(file_str)
                file_name = f"{uuid.uuid4().hex[:10]}.{ext}"
                data = ContentFile(file_data, name=file_name)
            except Exception:
                raise ValidationError("Invalid base64 file data")
        return super().to_internal_value(data)