from rest_framework_simplejwt import views as jwt_views
from django.urls import path, include
from rest_framework.routers import DefaultRouter

router = DefaultRouter()

from .views import (
    UserViewSet,
    UserInfoView,
    SendOTPView,
    VerifyOTPView,
    AddressViewSet,
    SendPhoneChangeOTPView,
    VerifyPhoneChangeOTPView,
    DeleteUserByPhoneOTPView,
    UserShareInfoView,
)

router.register(r"all", UserViewSet, basename="all")
router.register(r"address", AddressViewSet, basename="address")
router.register(r"share-info", UserShareInfoView, basename="share-info")

urlpatterns = [
    path("token/", jwt_views.TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", jwt_views.TokenRefreshView.as_view(), name="token_refresh"),
    path("profile/", UserInfoView.as_view(), name="profile"),
    path("send-otp/", SendOTPView.as_view(), name="send_otp"),
    path("verify-otp/", VerifyOTPView.as_view(), name="verify_otp"),
    path(
        "delete-by-otp/", DeleteUserByPhoneOTPView.as_view(), name="delete_user_by_otp"
    ),
    path(
        "change-phone/send-otp/",
        SendPhoneChangeOTPView.as_view(),
        name="send-phone-change-otp",
    ),
    path(
        "change-phone/verify-otp/",
        VerifyPhoneChangeOTPView.as_view(),
        name="verify-phone-change-otp",
    ),
    path("", include(router.urls)),
]
