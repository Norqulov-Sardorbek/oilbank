from rest_framework import serializers
from .custom_base_serializer import BaseOdooIDSerializer, Base64ImageField
from app.models.company_info import (
    Branch, 
    AboutUs, 
    CompanyComment, 
    CompanyBenefit, 
    FAQ,
    PrivacyPolicy,
    StaticPage,
    SupportContact,
    UserAgreement,
    LandingPageBanner,
)


class BranchSerializer(BaseOdooIDSerializer):
    parent_branch = serializers.SlugRelatedField(
        queryset=Branch.objects.all(),
        slug_field="odoo_id",
        required=False,
        allow_null=True,
    )
    image = Base64ImageField(required=False, allow_null=True)

    class Meta:
        model = Branch
        fields = "__all__"


class AboutUsSerializer(BaseOdooIDSerializer):
    class Meta:
        model = AboutUs
        fields = "__all__"


class CompanyCommentSerializer(BaseOdooIDSerializer):
    company_logo = Base64ImageField(required=False, allow_null=True)
    avatar = Base64ImageField(required=False, allow_null=True)

    class Meta:
        model = CompanyComment
        fields = "__all__"


class CompanyBenefitSerializer(BaseOdooIDSerializer):
    image = Base64ImageField(required=False, allow_null=True)

    class Meta:
        model = CompanyBenefit
        fields = "__all__"


class FAQSerializer(BaseOdooIDSerializer):
    class Meta:
        model = FAQ
        fields = "__all__"

    
class PrivacyPolicySerializer(BaseOdooIDSerializer):
    class Meta:
        model = PrivacyPolicy
        fields = "__all__"

    def validate(self, attrs):
        # allow partial updates: merge with instance data first
        data = {
            **({
                "title_en": getattr(self.instance, "title_en", None),
                "title_uz": getattr(self.instance, "title_uz", None),
                "title_ru": getattr(self.instance, "title_ru", None),
            } if self.instance else {}),
            **attrs,
        }

        # Optional: at least one title present (you can remove if not needed)
        if not any([data.get("title_en"), data.get("title_uz"), data.get("title_ru")]):
            raise serializers.ValidationError(
                {"title_en": "At least one title (en/uz/ru) must be provided."}
            )
        return attrs
    

class StaticPageSerializer(BaseOdooIDSerializer):
    image = Base64ImageField(required=False, allow_null=True)

    class Meta:
        model = StaticPage
        fields = "__all__"

    def validate(self, attrs):
        return attrs
    

class SupportContactSerializer(BaseOdooIDSerializer):
    class Meta:
        model = SupportContact
        fields = "__all__"


class UserAgreementSerializer(BaseOdooIDSerializer):
    class Meta:
        model = UserAgreement
        fields = "__all__"


class LandingPageBannerSerializer(BaseOdooIDSerializer):
    image = Base64ImageField(required=True)

    class Meta:
        model = LandingPageBanner
        fields = "__all__"