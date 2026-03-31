import base64
import uuid
from django.core.files.base import ContentFile
from rest_framework import serializers
from app.models.company_info import (
    UserAgreement,
    PrivacyPolicy,
    FAQ,
    Branch,
    Contact,
    SupportContact,
    Document,
    CompanyBenefit,
    CompanyComment,
    WebPageInfo, 
    StaticPage, 
    RequestForm,
    LandingPageBanner,
)
from app.models.booking import AppointmentWorkingDay, Appointment
from django.utils.translation import get_language
from django.utils import timezone


class BranchSerializer(serializers.ModelSerializer):
    day_from = serializers.SerializerMethodField(read_only=True)
    day_to = serializers.SerializerMethodField(read_only=True)
    time_from = serializers.SerializerMethodField(read_only=True)
    time_to = serializers.SerializerMethodField(read_only=True)
    is_open_today = serializers.SerializerMethodField(read_only=True)
    image = serializers.SerializerMethodField()
    name_lang = serializers.SerializerMethodField()

    class Meta:
        model = Branch
        fields = [
            'id',
            'odoo_id',
            'image',
            'name',
            'name_uz',
            'name_ru',
            'longitude',
            'latitude',
            'yandex_link',
            'google_link',
            'created_at',
            'updated_at',
            'order_expiration_days',
            'day_from',
            'day_to',
            'time_from',
            'time_to',
            'is_open_today',
            'contacts',
            'category',
            'name_lang',
        ]
        extra_kwargs = {
            'image': {'write_only': True},  # Base64 only for input
            'name_lang':{'name_lang':False},
            'day_from': {'required': False},
            'day_to': {'required': False},
            'time_from': {'required': False},
            'time_to': {'required': False},
            'is_open_today': {'required': False}
        }

    def get_image(self, obj):
        if obj.image:
            return self.context["request"].build_absolute_uri(obj.image.url)
        return None
    
    def get_name_lang(self,obj):
        language = get_language()
        if language not in ['en', 'uz', 'ru']:
            language = 'en'
        if language == 'uz':
            return obj.name_uz if obj.name_uz else obj.name
        if language == 'ru':
            return obj.name_ru if obj.name_ru else obj.name
        return obj.name
    def to_internal_value(self, data):
        """Handle base64 image conversion before validation"""
        data = data.copy()
        image_data = data.get("image")

        if (
            image_data
            and isinstance(image_data, str)
            and image_data.startswith("data:image")
        ):
            format, imgstr = image_data.split(";base64,")
            ext = format.split("/")[-1]
            data["image"] = ContentFile(
                base64.b64decode(imgstr), name=f"{uuid.uuid4()}.{ext}"
            )

        return super().to_internal_value(data)

    def get_primary_appointment(self, obj):
        """Get the primary appointment (e.g., oil change) for this branch"""
        return Appointment.objects.filter(branch=obj).order_by("-id").first()

    def get_day_range(self, obj):
        """Helper method to get first and last working days from appointment"""
        appointment = self.get_primary_appointment(obj)
        if not appointment:
            return None, None

        working_days = appointment.working_days.order_by("day")
        if working_days.exists():
            first_day = working_days.first().get_day_display()
            last_day = working_days.last().get_day_display()
            return first_day, last_day
        return None, None

    def get_todays_hours(self, obj):
        appointment = self.get_primary_appointment(obj)
        if not appointment:
            return []

        today = timezone.now().weekday()
        return appointment.working_days.filter(day=today).order_by("opening_time")

    def get_day_from(self, obj):
        return self.get_day_range(obj)[0]

    def get_day_to(self, obj):
        return self.get_day_range(obj)[1]

    def get_time_from(self, obj):
        todays_hours = self.get_todays_hours(obj)
        return (
            min((wd.opening_time for wd in todays_hours), default=None)
            if todays_hours
            else None
        )

    def get_time_to(self, obj):
        todays_hours = self.get_todays_hours(obj)
        return (
            max((wd.closing_time for wd in todays_hours), default=None)
            if todays_hours
            else None
        )

    def get_is_open_today(self, obj):
        todays_hours = self.get_todays_hours(obj)
        return bool(todays_hours)


class BranchListSerializer(serializers.ModelSerializer):
    distance_km = serializers.SerializerMethodField()
    branch_id = serializers.IntegerField(source="id")
    image = serializers.SerializerMethodField()
    name_lang = serializers.SerializerMethodField()

    class Meta:
        model = Branch
        fields = [
            "id",
            "name",
            "branch_id",
            "image",
            "distance_km",
            "order_expiration_days",
            "google_link",
            "yandex_link",
            "latitude",
            "longitude",
            "name_lang",
        ]

    def get_distance_km(self, obj):
        distance_map = self.context.get("distance_map", {})
        return distance_map.get(obj.id)

    def get_name_lang(self,obj):
        language = get_language()
        if language not in ['en', 'uz', 'ru']:
            language = 'en'
        if language=='uz':
            return obj.name_uz if obj.name_uz else obj.name
        if language=='ru':
            return obj.name_ru if obj.name_ru else obj.name
        return obj.name

    def get_image(self, obj):
        if obj.image:
            request = self.context.get("request")
            return (
                request.build_absolute_uri(obj.image.url) if request else obj.image.url
            )
        return None


class BranchOutputSerializer(BranchListSerializer):
    name_lang = serializers.SerializerMethodField()

    class Meta:
        model = Branch
        fields = [
            "id",
            "name",
            "image",
            "order_expiration_days",
            "google_link",
            "yandex_link",
            "latitude",
            "longitude",
            "name_lang",
        ]

    def get_name_lang(self,obj):
        language = get_language()
        if language not in ['en', 'uz', 'ru']:
            language = 'en'
        if language=='uz':
            return obj.name_uz if obj.name_uz else obj.name
        if language=='ru':
            return obj.name_ru if obj.name_ru else obj.name
        return obj.name

class FAQSerializer(serializers.ModelSerializer):
    question = serializers.SerializerMethodField()
    answer = serializers.SerializerMethodField()

    class Meta:
        model = FAQ
        fields = [
            "id",
            "question",
            "answer",
            "created_at",
            "updated_at",
            "order_number",
        ]

    def get_language_field(self, instance, field_name):
        language = get_language()
        if language not in ["en", "uz", "ru"]:
            language = "en"
        field = f"{field_name}_{language}"
        return getattr(instance, field, None)

    def get_question(self, instance):
        return self.get_language_field(instance, "question")

    def get_answer(self, instance):
        return self.get_language_field(instance, "answer")


class FAQCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQ
        fields = [
            "question_en",
            "question_uz",
            "question_ru",
            "answer_en",
            "answer_uz",
            "answer_ru",
            "order_number",
        ]


class UserAgreementSerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()

    class Meta:
        model = UserAgreement
        fields = ["id", "title", "description", "created_at", "updated_at"]

    def get_language_field(self, instance, field_name):
        language = get_language()
        if language not in ["en", "uz", "ru"]:
            language = "en"
        field = f"{field_name}_{language}"
        return getattr(instance, field, None)

    def get_title(self, instance):
        return self.get_language_field(instance, "title")

    def get_description(self, instance):
        return self.get_language_field(instance, "description")


class PrivacyPolicySerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()

    class Meta:
        model = PrivacyPolicy
        fields = ["id", "title", "description", "created_at", "updated_at"]

    def get_language_field(self, instance, field_name):
        language = get_language()
        if language not in ["en", "uz", "ru"]:
            language = "en"
        field = f"{field_name}_{language}"
        return getattr(instance, field, None)

    def get_title(self, instance):
        return self.get_language_field(instance, "title")

    def get_description(self, instance):
        return self.get_language_field(instance, "description")


class ContactSerializer(serializers.ModelSerializer):

    class Meta:
        model = Contact
        fields = [
            "id",
            "phone1",
            "phone2",
            "email1",
            "email2",
            "telegram_bot",
            "telegram",
            "recrutement",
            "instagram",
            "facebook",
            "address",
            "yandex_link",
            "google_link",
            "app_google_play_link",
            "app_app_store_link",
        ]


class SupportContactSerializer(serializers.ModelSerializer):

    class Meta:
        model = SupportContact
        fields = ["phone", "email", "support_chat_url"]


class DocumentOutputSerializer(serializers.ModelSerializer):
    file_name = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = ["id", "file_name", "file", "created_at"]

    def get_file_name(self, obj):
        lang = get_language()
        if lang == "ru":
            return obj.file_name_ru
        elif lang == "en":
            return obj.file_name_en
        return obj.file_name_uz


class DocumentInputSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = [
            "id",
            "file_name_uz",
            "file_name_ru",
            "file_name_en",
            "file",
            "created_at",
        ]
        read_only_fields = ["id", "created_at", "admin"]


class ProductQuantitySerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField()


class ProductListRequestSerializer(serializers.Serializer):
    products = ProductQuantitySerializer(many=True)


class CompanyBenefitSerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()

    class Meta:
        model = CompanyBenefit
        fields = ["id", "image", "title", "description", "created_at", "updated_at"]

    def get_title(self, obj):
        lang = (
            self.context["request"].META.get("HTTP_ACCEPT_LANGUAGE", "en").lower()[:2]
        )
        if lang == "ru" and obj.title_ru:
            return obj.title_ru
        elif lang == "uz" and obj.title_uz:
            return obj.title_uz
        return obj.title_en or obj.title_ru or obj.title_uz or ""

    def get_description(self, obj):
        lang = (
            self.context["request"].META.get("HTTP_ACCEPT_LANGUAGE", "en").lower()[:2]
        )
        if lang == "ru" and obj.description_ru:
            return obj.description_ru
        elif lang == "uz" and obj.description_uz:
            return obj.description_uz
        return obj.description_en or obj.description_ru or obj.description_uz or ""


class CompanyCommentSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    comment = serializers.SerializerMethodField()
    position = serializers.SerializerMethodField()

    class Meta:
        model = CompanyComment
        fields = [
            "id",
            "company_name",
            "company_logo",
            "avatar",
            "full_name",
            "comment",
            "position",
        ]

    def get_full_name(self, obj):
        language = (
            self.context["request"].META.get("HTTP_ACCEPT_LANGUAGE", "en").lower()
        )
        if language.startswith("uz"):
            return obj.full_name_uz
        elif language.startswith("ru"):
            return obj.full_name_ru
        return obj.full_name_en

    def get_comment(self, obj):
        language = (
            self.context["request"].META.get("HTTP_ACCEPT_LANGUAGE", "en").lower()
        )
        if language.startswith("uz"):
            return obj.comment_uz
        elif language.startswith("ru"):
            return obj.comment_ru
        return obj.comment_en

    def get_position(self, obj):
        language = (
            self.context["request"].META.get("HTTP_ACCEPT_LANGUAGE", "en").lower()
        )
        if language.startswith("uz"):
            return obj.position_uz
        elif language.startswith("ru"):
            return obj.position_ru
        return obj.position_en


class WebPageInfoSerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()

    class Meta:
        model = WebPageInfo
        fields = ["id", "title", "url"]

    def get_language_field(self, instance, field_name):
        language = get_language()
        if language not in ["en", "uz", "ru"]:
            language = "en"
        field = f"{field_name}_{language}"
        return getattr(instance, field, None)

    def get_title(self, instance):
        return self.get_language_field(instance, "title")

    def get_url(self, instance):
        return self.get_language_field(instance, "url")


class WebPageInfoInputSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebPageInfo
        fields = ["id", "title_en", "title_uz", "title_ru", "url_en", "url_uz", "url_ru"]


class StaticPageSerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()
    subtitle = serializers.SerializerMethodField()
    content = serializers.SerializerMethodField()

    class Meta:
        model = StaticPage
        fields = ['id', 'title', 'subtitle', 'content', 'slug', 'include_form', 'image']

    def get_language_field(self, instance, field_name):
        language = get_language() or 'en'
        field = getattr(instance, f"{field_name}_{language}", None)
        return field or getattr(instance, f"{field_name}_en", None)

    def get_title(self, obj):
        return self.get_language_field(obj, "title")

    def get_subtitle(self, obj):
        return self.get_language_field(obj, "subtitle")

    def get_content(self, obj):
        return self.get_language_field(obj, "content")


class StaticPageListSerializer(StaticPageSerializer):
    class Meta(StaticPageSerializer.Meta):
        fields = ['id', 'title', 'subtitle', 'slug']


class RequestFormSerializer(serializers.ModelSerializer):
    source_page = serializers.SlugRelatedField(
        queryset=StaticPage.objects.all(),
        slug_field="slug",
        required=False,
        allow_null=True
    )
    class Meta:
        model = RequestForm
        fields = ['id', 'name', 'commentary', 'organization', 'phone', 'email', 'source_page', "source"]


class LandingPageBannerSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = LandingPageBanner
        fields = ["id", "image_url", "link", "order_number"]

    def get_image_url(self, obj):
        if not obj.image:
            return None
        request = self.context.get("request")
        url = obj.image.url
        return request.build_absolute_uri(url) if request else url