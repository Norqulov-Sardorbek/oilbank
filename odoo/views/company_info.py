from rest_framework import viewsets
from django_filters.rest_framework import DjangoFilterBackend
from ..custom_filter import OdooIDFilterSet
from rest_framework.permissions import AllowAny
from .custom_base_viewset import OdooBaseViewSet
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
from odoo.serializers.company_info import (
    BranchSerializer, 
    AboutUsSerializer, 
    CompanyCommentSerializer, 
    CompanyBenefitSerializer, 
    FAQSerializer,
    PrivacyPolicySerializer,
    StaticPageSerializer,
    SupportContactSerializer,
    UserAgreementSerializer,
    LandingPageBannerSerializer,
)


class BranchOdooViewSet(OdooBaseViewSet):
    permission_classes = [AllowAny]
    queryset = Branch.objects.all()
    serializer_class = BranchSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = OdooIDFilterSet
    lookup_field = "odoo_id"


class AboutUsOdooViewSet(OdooBaseViewSet):
    permission_classes = [AllowAny]
    queryset = AboutUs.objects.all()
    serializer_class = AboutUsSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = OdooIDFilterSet
    lookup_field = "odoo_id"


class CompanyCommentOdooViewSet(OdooBaseViewSet):
    permission_classes = [AllowAny]
    queryset = CompanyComment.objects.all()
    serializer_class = CompanyCommentSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = OdooIDFilterSet
    lookup_field = "odoo_id"



class CompanyBenefitOdooViewSet(OdooBaseViewSet):
    permission_classes = [AllowAny]
    queryset = CompanyBenefit.objects.all()
    serializer_class = CompanyBenefitSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = OdooIDFilterSet
    lookup_field = "odoo_id"


class FAQOdooViewSet(OdooBaseViewSet):
    permission_classes = [AllowAny]
    queryset = FAQ.objects.all()
    serializer_class = FAQSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = OdooIDFilterSet
    lookup_field = "odoo_id"


class PrivacyPolicyOdooViewSet(OdooBaseViewSet):
    permission_classes = [AllowAny]
    queryset = PrivacyPolicy.objects.all()
    serializer_class = PrivacyPolicySerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = OdooIDFilterSet
    lookup_field = "odoo_id"


class StaticPageOdooViewSet(OdooBaseViewSet):
    permission_classes = [AllowAny]
    queryset = StaticPage.objects.all()
    serializer_class = StaticPageSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = OdooIDFilterSet
    lookup_field = "odoo_id"


class SupportContactOdooViewSet(OdooBaseViewSet):
    permission_classes = [AllowAny]
    queryset = SupportContact.objects.all()
    serializer_class = SupportContactSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = OdooIDFilterSet
    lookup_field = "odoo_id"


class UserAgreementOdooViewSet(OdooBaseViewSet):
    permission_classes = [AllowAny]
    queryset = UserAgreement.objects.all()
    serializer_class = UserAgreementSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = OdooIDFilterSet
    lookup_field = "odoo_id"


class LandingPageBannerOdooViewSet(OdooBaseViewSet):
    permission_classes = [AllowAny]
    queryset = LandingPageBanner.objects.all()
    serializer_class = LandingPageBannerSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = OdooIDFilterSet
    lookup_field = "odoo_id"