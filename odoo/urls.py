from django.urls import path, include
from rest_framework.routers import DefaultRouter

router = DefaultRouter()

from .views.user_views import UserViewSet, AddressViewSet
from .views.stories_views import StoryOdooViewSet
from .views.notification import NotificationViewSet, NotificationTemplateViewSet
from .views.card import BalanceViewSet, CashbackViewSet, BalanceStatusViewSet
from .views.product_views import (
    VariantViewSet,
    OptionViewSet,
    ProductOptionViewSet,
    ProductVariantsViewSet,
    ProductTemplateViewSet,
    WareHouseViewSet,
    LocationViewSet,
    ProductOptionApi,
    CategoryViewSet,
    ProductViewSet,
    StockQuantityViewSet,
    PriceListViewSet,
    CurrencyViewSet,
    DiscountViewSet,
    OilBrandViewSet,
    ProductDeleteApi,
    FilterBrandViewSet,
    BrandViewSet,
    ProductTemplateImageViewSet,
    OfferOdooViewSet,
    PartnerOdooViewSet,
)
from .views.company_info import (
    BranchOdooViewSet, 
    AboutUsOdooViewSet, 
    CompanyCommentOdooViewSet,
    CompanyBenefitOdooViewSet,
    FAQOdooViewSet,
    PrivacyPolicyOdooViewSet,
    StaticPageOdooViewSet,
    SupportContactOdooViewSet,
    UserAgreementOdooViewSet,
    LandingPageBannerOdooViewSet,
)
from .views.order import (
    RegionViewSet,
    DistrictViewSet,
    DeliveryPriceViewSet,
    OrderViewSet,
    OrderItemViewSet,
    RatingViewSet,
    OrderRatingViewSet, 
    LoyaltyProgramViewSet, 
    PromoRewardViewSet, 
    PromoCodeViewSet,
    LoyaltyRuleViewSet,
)
from .views.appointment import (
    AppointmentViewSet,
    AppointmentWorkingDayViewSet,
    ResourceViewSet,
)
from .views.garage import (
    FirmViewSet,
    CarModelViewSet,
    SomeColorViewSet,
    CarColorViewSet,
    CarViewSet,
    OilChangedHistoryViewSet,
)


router.register(r"brands", BrandViewSet, basename="brands")
router.register(r"attribute", VariantViewSet, basename="variants")
router.register(r"options", OptionViewSet, basename="options")
router.register(r"product-options", ProductOptionViewSet, basename="product-options")
router.register(r"product-attribute", ProductVariantsViewSet, basename="product-variants")
router.register(r"product-options", ProductOptionViewSet, basename="product-options")
# router.register(r'product-variants',ProductVariantsViewSet,basename='product-variants')
router.register(r"users", UserViewSet, basename="users")
router.register(r"notifications", NotificationViewSet, basename="notifications")
router.register(r"notification-templates", NotificationTemplateViewSet, basename="notification-templates")
router.register(r"warehouse", WareHouseViewSet, basename="warehouse")
router.register(r"categories", CategoryViewSet, basename="categories")
router.register(r"story", StoryOdooViewSet, basename="story")
router.register(r"product-template", ProductTemplateViewSet, basename="product-template")
router.register(r"branch", BranchOdooViewSet, basename="branch")
router.register(r"location", LocationViewSet, basename="location")
router.register(r"product", ProductViewSet, basename="product")
router.register(r"stock-quantity", StockQuantityViewSet, basename="stock-quantity")
router.register(r"price-list", PriceListViewSet, basename="price-list")
router.register(r"currency", CurrencyViewSet, basename="currency")
router.register(r"discount", DiscountViewSet, basename="discount")
router.register(r"region", RegionViewSet, basename="region")
router.register(r"district", DistrictViewSet, basename="district")
router.register(r"delivery-price", DeliveryPriceViewSet, basename="delivery-price")
router.register(r"oil-brand", OilBrandViewSet, basename="oil-brand")
router.register(r"filter-brand", FilterBrandViewSet, basename="filter-brand")
router.register(r"cashback", CashbackViewSet, basename="cashback")
router.register(r"balance", BalanceViewSet, basename="balance")
router.register(r"balance-status", BalanceStatusViewSet, basename="balance-status")
router.register(r"appointments", AppointmentViewSet, basename="appointment")
router.register(r"working-days", AppointmentWorkingDayViewSet, basename="working-day")
router.register(r"resources", ResourceViewSet, basename="resource")
router.register(r"firms", FirmViewSet, basename="firm")
router.register(r"car-models", CarModelViewSet, basename="car-model")
router.register(r"some-colors", SomeColorViewSet, basename="some-color")
router.register(r"car-colors", CarColorViewSet, basename="car-color")
router.register(r"cars", CarViewSet, basename="car")
router.register(r"oil-changed-histories", OilChangedHistoryViewSet, basename="oilchange")
router.register(r"address", AddressViewSet, basename="address")
router.register(r"order", OrderViewSet, basename="order")
router.register(r"order-items", OrderItemViewSet, basename="order-items")
router.register(r"rating-type", RatingViewSet, basename="rating-type")
router.register(r"order-rating", OrderRatingViewSet, basename="order-rating")
router.register(r"product-images",ProductTemplateImageViewSet,basename="product-images")
router.register(r'loyalty-programs', LoyaltyProgramViewSet,basename='loyalty-programs')
router.register(r'promo-rewards', PromoRewardViewSet,basename='promo-rewards')
router.register(r'promocodes', PromoCodeViewSet,basename='promocodes')
router.register(r'loyalty-rules', LoyaltyRuleViewSet,basename='loyalty-rules')
router.register(r"aboutus", AboutUsOdooViewSet, basename="aboutus")
router.register(r"company-comment", CompanyCommentOdooViewSet, basename="company-comment")
router.register(r"company-benefit", CompanyBenefitOdooViewSet, basename="company-benefit")
router.register(r"faq", FAQOdooViewSet, basename="faq")
router.register(r"offer", OfferOdooViewSet, basename="offer")
router.register(r"product-partner", PartnerOdooViewSet, basename="product-partner")
router.register(r"privacy-policy", PrivacyPolicyOdooViewSet, basename="privacy-policy")
router.register(r"static-page", StaticPageOdooViewSet, basename="static-page")
router.register(r"support-contact", SupportContactOdooViewSet, basename="support-contact")
router.register(r"user-agreement", UserAgreementOdooViewSet, basename="user-agreement")
router.register(r"landing-page-banner", LandingPageBannerOdooViewSet, basename="landing-page-banner")


urlpatterns = [
    path("product-option-api/", ProductOptionApi.as_view(), name="product-option-api"),
    path("product-delete/", ProductDeleteApi.as_view(), name="product-delete"),
    path("", include(router.urls)),
]
