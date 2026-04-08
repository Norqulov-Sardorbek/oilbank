from django.urls import include, path
from rest_framework.routers import DefaultRouter
from app.views.story import StoryViewSet, StoryVideoView
from app.views.app_version_check import check_app_version
from app.views.notification import NotificationViewSet, NotificationTemplateViewSet
from app.views.booking import BookingRatingViewSet, BookingViewSet, WeeklySlotsAPIView
from app.views.card import (
    CardViewSet,
    BalanceViewSet,
    CashbackViewSet,
    BalanceStatusViewSet,
)
from app.views.garage import (
    CarViewSet,
    OilChangedHistoryViewSet,
    CarModelViewSet,
    FirmViewSet,
    CarColorViewSet,
    OilChangeRatingViewSet,
)
from app.views.company_info import (
    BranchViewSet,
    UserAgreementListView,
    PrivacyPolicyListView,
    FAQManageView,
    ContactViewSet,
    CombinedSupportInfoView,
    DocumentViewSet,
    ContentViewSet,
    CompanyCommentViewSet,
    WebPageInfoViewSet,
    StaticPageViewSet,
    RequestFormCreateView,
    LandingPageBannerListAPIView,
)
from app.views.product import (
    SavedProductListView,
    SavedProductToggleView,
    BulkSavedProductToggleView,
    DiscountViewset,
    CategoryViewSet,
    ProductViewSet,
    ProductTemplateViewSet,
    BrandViewSet,
    OfferViewSet,
    SimilarProductViewSet,
    ProductRatingViewSet,
    VariantViewSet,
    OilBrandViewSet,
    SearchAPIView,
    SimilarProductTemplatesViewSet,
    PartnerViewSet
)
from app.views.order import (
    OrderViewSet,
    OrderRatingViewSet,
    RegionViewSet,
    DistrictViewSet,
    BasketViewSet,
    OrderMulticardResponceApiView,
    ReseaveMulticardCardPaymentOPT,
    PromoCodeViewSet,
    DeliveryPriceViewSet,
    OrderPaymentApiView,
    rating_type_list, 
    LoyaltyProgramViewSet, 
    PromoRewardViewSet,
)
from app.views.qr_codes import QRCodeViewSet
from app.views.edu_video import EduVideoViewSet
router = DefaultRouter()

router.register(r"notifications", NotificationViewSet, basename="notification")
router.register(r"notification-templates", NotificationTemplateViewSet, basename="notification-template")
router.register(r"cars", CarViewSet, basename="cars")
router.register(r"car-colors", CarColorViewSet, basename="car-colors")
router.register(r"oil-changes", OilChangedHistoryViewSet, basename="oilchange")
router.register(r"story", StoryViewSet, basename="story")
router.register(r"branch", BranchViewSet, basename="branch")
router.register(r"car-model", CarModelViewSet, basename="carmodel")
router.register(r"firm", FirmViewSet, basename="firm")
router.register(r"faq", FAQManageView, basename="faq")
router.register(r"contact", ContactViewSet, basename="contact")
router.register(r"discounts", DiscountViewset, basename="discount")
router.register(r"categories", CategoryViewSet, basename="category")
router.register(r"products", ProductViewSet, "product")
router.register(r"booking-rating", BookingRatingViewSet, basename="bookingrating")
router.register(r"documents", DocumentViewSet, basename="documents")
router.register(r"product-templates", ProductTemplateViewSet, basename="product-template")
router.register(r"partners", PartnerViewSet, basename="partner")
router.register(r"orders", OrderViewSet, basename="order")
router.register(r"regions", RegionViewSet, basename="region")
router.register(r"districts", DistrictViewSet, basename="district")
router.register(r"brands", BrandViewSet, basename="brand")
router.register(r"order-ratings", OrderRatingViewSet, basename="order-rating")
router.register(r"basket", BasketViewSet, basename="basket")
router.register(r"offers", OfferViewSet, basename="offer")
router.register(r"cards", CardViewSet, basename="card")
router.register(r"booking", BookingViewSet, basename="booking")
router.register(r"promocodes", PromoCodeViewSet, basename="promocode")
router.register(r"loyalty-promocodes", LoyaltyProgramViewSet, basename="loyalty-promocode")
router.register(r"promo-rewards", PromoRewardViewSet, basename="promo-reward")
router.register(r"product-ratings", ProductRatingViewSet, basename="product-rating")
router.register(r"delivery-price", DeliveryPriceViewSet, basename="delivery-price")
router.register(r"oil-brand", OilBrandViewSet, basename="oil-brand")
router.register(r"balance-status", BalanceStatusViewSet, basename="balance-status")
router.register(r"balances", BalanceViewSet, basename="balances")
router.register(r"cashbacks", CashbackViewSet, basename="cashbacks")
router.register(r"company-benefit", ContentViewSet, basename="company-benefit")
router.register(r"company-comment", CompanyCommentViewSet, basename="company-comment")
router.register(r"web-page-info", WebPageInfoViewSet, basename="web-page-info")
router.register(r"static-pages", StaticPageViewSet, basename="static-page")
router.register(r"oil-change-rating", OilChangeRatingViewSet, basename="oil-change-rating")
router.register(r"edu-videos", EduVideoViewSet, basename="edu-video")
router.register(r"qr-codes", QRCodeViewSet, basename="qr-code")
urlpatterns = [
    path("", include(router.urls)),
    path("saved-products/", SavedProductListView.as_view(), name="saved-products"),
    path("order/pay/", OrderPaymentApiView.as_view(), name="order-payment"),
    path("saved-products/toggle/", SavedProductToggleView.as_view(), name="saved-products-toggle"),
    path("saved-products/bulk-toggle/", BulkSavedProductToggleView.as_view(), name="bulk-saved-products-toggle"),
    path("user-agreement/", UserAgreementListView.as_view(), name="user-agreement"),
    path("privacy-policy/", PrivacyPolicyListView.as_view(), name="privacy-policy"),
    path("support-info/", CombinedSupportInfoView.as_view(), name="support-info"),
    path("multicard/invoice-response/", OrderMulticardResponceApiView.as_view(), name="multicard-responce"),
    path("card-otp/confirm/", ReseaveMulticardCardPaymentOPT.as_view(), name="card-otp/confirm/"),
    path("branches/<int:branch_id>/weekly-slots/", WeeklySlotsAPIView.as_view(), name="weekly-slots"),
    path("stories/<int:pk>/video/", StoryVideoView.as_view(), name="story-video"),
    path("products/<str:product_ids>/similar/", SimilarProductViewSet.as_view({"get": "list"}), name="similar-products"),
    path("similar-product-templates/",SimilarProductTemplatesViewSet.as_view({"get": "list"}),name="similar-product-tmeplates"),
    path("app-version-check/", check_app_version, name="app-version-check"),
    path("variants/", VariantViewSet.as_view({"get": "list"}), name="variants"),
    path("search/", SearchAPIView.as_view(), name="search"),
    path("rating-types/", rating_type_list, name="rating-type-list-func"),
    path('request-form/', RequestFormCreateView.as_view(), name='request-form'),
    path("landing-banners/", LandingPageBannerListAPIView.as_view(), name="landing-banners"),
]

