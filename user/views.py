# global imports
from rest_framework import viewsets, serializers
from rest_framework.exceptions import MethodNotAllowed, ValidationError
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
from datetime import timedelta
import random
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiExample
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from drf_spectacular.types import OpenApiTypes
from django.utils.translation import gettext_lazy as _

from app.utils.notification_utils import create_notification


# local imports
from .models import NotificationMessages, UserInfo, User, Address, OTP, UserShareInfo
from .serializers import (
    NotificationMessagesSerializer,
    UserSerializer,
    UserInfoSerializer,
    SendOTPSerializer,
    UserShareInfoSerializer,
    VerifyOTPSerializer,
    AddressSerializer,
    ChangePhoneSerializer,
    ChangePhoneVerifyOTPSerializer,
    DeleteUserByPhoneOTPSerializer,
)
from user.tasks import send_sms


@extend_schema_view(
    list=extend_schema(
        summary="List users",
        description="List all users (admin only)",
        responses={200: UserSerializer(many=True)},
        tags=["Admin"],
    ),
    retrieve=extend_schema(
        summary="Retrieve user",
        description="Get user details (admin only)",
        responses={200: UserSerializer},
        tags=["Admin"],
    ),
    create=extend_schema(
        summary="Create user",
        description="Create new user (admin only)",
        request=UserSerializer,
        responses={201: UserSerializer},
        tags=["Admin"],
    ),
    update=extend_schema(
        summary="Update user",
        description="Full update of user (admin only)",
        request=UserSerializer,
        responses={200: UserSerializer},
        tags=["Admin"],
    ),
    partial_update=extend_schema(
        summary="Partial update user",
        description="Partial update of user (admin only)",
        request=UserSerializer,
        responses={200: UserSerializer},
        tags=["Admin"],
    ),
    destroy=extend_schema(
        summary="Delete user",
        description="Delete user (admin only)",
        responses={204: None},
        tags=["Admin"],
    ),
)
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    permission_classes = [IsAdminUser]
    serializer_class = UserSerializer


@extend_schema_view(
    list=extend_schema(
        summary="Get user info",
        description="Get current user's profile information",
        responses={200: UserInfoSerializer(many=True)},
        tags=["User Profile"],
    ),
    retrieve=extend_schema(
        summary="Retrieve user info",
        description="Get user profile details",
        responses={200: UserInfoSerializer},
        tags=["User Profile"],
    ),
    create=extend_schema(
        summary="Create user info",
        description="Create user profile information",
        request=UserInfoSerializer,
        responses={201: UserInfoSerializer},
        tags=["User Profile"],
    ),
    update=extend_schema(
        summary="Update user info",
        description="Full update of user profile",
        request=UserInfoSerializer,
        responses={200: UserInfoSerializer},
        tags=["User Profile"],
    ),
    partial_update=extend_schema(
        summary="Partial update user info",
        description="Partial update of user profile",
        request=UserInfoSerializer,
        responses={200: UserInfoSerializer},
        tags=["User Profile"],
    ),
    destroy=extend_schema(
        summary="Delete user info",
        description="Delete user profile information",
        responses={204: None},
        tags=["User Profile"],
    ),
)
class UserInfoView(APIView):
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.request.method == "POST":
            return [AllowAny()]
        return [IsAuthenticated()]

    @extend_schema(
        description="Get the current authenticated user's profile. Returns the user information if it exists.",
    )
    def get(self, request):
        try:
            user_info = UserInfo.objects.filter(user=request.user).first()
            if user_info:
                serializer = UserInfoSerializer(
                    user_info, context={"request": self.request}
                )
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(
                    {"error": "User info not found"}, status=status.HTTP_404_NOT_FOUND
                )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        description="Create user profile information for a new user. Requires `user_id` in the request data.",
        request=UserInfoSerializer,
        responses={
            201: UserInfoSerializer,
            400: "Invalid request, e.g., missing `user_id`.",
        },
    )
    def post(self, request):
        try:
            user_id = request.data.get("user_id")

            if not user_id:
                return Response(
                    {"error": "user_id is required"}, status=status.HTTP_400_BAD_REQUEST
                )

            user = User.objects.get(id=user_id)

            user_info = UserInfo.objects.filter(user=user).first()

            if user_info:
                return Response(
                    {"error": "User info already exists"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            serializer = UserInfoSerializer(
                data=request.data, context={"user": user, "request": self.request}
            )
            serializer.is_valid(raise_exception=True)

            user_info = serializer.save(user=user)
            refresh = RefreshToken.for_user(user)
            response_data = {
                "user_info": user_info.id,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            }

            return Response(response_data, status=status.HTTP_201_CREATED)

        except User.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )
        except ValidationError as e:
            return Response({"error": e.detail}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        description="Update the full user profile. Requires complete user profile data.",
        request=UserInfoSerializer,
        responses={
            200: UserInfoSerializer,
            400: "Invalid request data.",
            404: "User info not found.",
        },
    )
    def put(self, request):
        try:
            user_info = UserInfo.objects.filter(user=request.user).first()
            if not user_info:
                return Response(
                    {"error": "User info not found"}, status=status.HTTP_404_NOT_FOUND
                )

            serializer = UserInfoSerializer(
                user_info,
                data=request.data,
                context={"user": request.user, "request": self.request},
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        description="Partially update the user profile. Only provided fields will be updated.",
        request=UserInfoSerializer,
        responses={
            200: UserInfoSerializer,
            400: "Invalid request data.",
            404: "User info not found.",
        },
    )
    def patch(self, request):
        try:
            user_info = UserInfo.objects.filter(user=request.user).first()
            if not user_info:
                return Response(
                    {"error": "User info not found"}, status=status.HTTP_404_NOT_FOUND
                )

            serializer = UserInfoSerializer(
                user_info,
                data=request.data,
                partial=True,
                context={"user": request.user, "request": self.request},
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        description="Deleting user info is not allowed.",
        responses={405: "Method Not Allowed"},
    )
    def delete(self, request):
        raise MethodNotAllowed(
            "DELETE", detail="You cannot delete your user information."
        )


@extend_schema(
    summary="Send OTP",
    description="Send OTP code to phone number for authentication",
    request=SendOTPSerializer,
    responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
    examples=[
        OpenApiExample(
            "Request Example",
            value={"phone": "+998901234567", "purpose": "login"},
            request_only=True,
        ),
        OpenApiExample(
            "Success Response",
            value={
                "message": _("OTP sent successfully"),
                "phone": "+998901234567",
                "seconds": 300,
            },
            response_only=True,
            status_codes=["200"],
        ),
        OpenApiExample(
            "Existing OTP Response",
            value={
                "message": _("You have a recent SMS that you can use"),
                "phone": "+998901234567",
                "seconds": 300,
            },
            response_only=True,
            status_codes=["200"],
        ),
    ],
    tags=["Authentication"],
)
class SendOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        purpose = request.data.get("purpose", "login")
        serializer = SendOTPSerializer(
            data=request.data, context={"request": request, "purpose": purpose}
        )
        if serializer.is_valid():
            otp, created, error = serializer.save()

            if error:
                return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)

            remaining_time = (otp.expired_at - timezone.now()).seconds

            if created:
                return Response(
                    {
                        "message": _("OTP sent successfully"),
                        "phone": request.data.get("phone"),
                        "seconds": remaining_time,
                    },
                    status=status.HTTP_200_OK,
                )
            else:
                return Response(
                    {
                        "message": _("You have a recent SMS that you can use"),
                        "phone": request.data.get("phone"),
                        "seconds": remaining_time,
                    },
                    status=status.HTTP_200_OK,
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    summary="Verify OTP",
    description="Verify OTP code and authenticate user",
    request=ChangePhoneVerifyOTPSerializer,
    responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
    examples=[
        OpenApiExample(
            "Request Example",
            value={"phone": "+998901234567", "code": "1234"},
            request_only=True,
        ),
        OpenApiExample(
            "Success Response",
            value={
                "message": "OTP verified successfully",
                "user": 1,
                "is_new": False,
                "access": "eyJhbGciOi...",
                "refresh": "eyJhbGciOi...",
            },
            response_only=True,
            status_codes=["200"],
        ),
    ],
    tags=["Authentication"],
)
class VerifyOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        if serializer.is_valid():
            result = serializer.save()
            return Response(
                {
                    "message": _("OTP verified successfully"),
                    "user": result["user"].id,
                    "is_new": result["is_new"],
                    "access": result["access"],
                    "refresh": result["refresh"],
                },
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DeleteUserByPhoneOTPView(APIView):
    permission_classes = [AllowAny]
    serializer_class = DeleteUserByPhoneOTPSerializer

    @swagger_auto_schema(
        operation_summary="Delete user via phone & OTP",
        operation_description="Deletes a user account by verifying OTP sent to the user's phone.",
        request_body=DeleteUserByPhoneOTPSerializer,
        responses={
            200: openapi.Response(
                description="User deleted successfully",
                examples={
                    "application/json": {
                        "message": "User account deleted successfully."
                    }
                },
            ),
            400: openapi.Response(
                description="Validation failed",
                examples={"application/json": {"code": ["Invalid OTP code."]}},
            ),
        },
    )
    def post(self, request):
        serializer = DeleteUserByPhoneOTPSerializer(data=request.data)
        if serializer.is_valid():
            try:
                serializer.delete_user()
                return Response(
                    {"message": _("User account deleted successfully.")},
                    status=status.HTTP_200_OK,
                )
            except serializers.ValidationError as e:
                return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema_view(
    list=extend_schema(
        summary="List of user addresses",
        description="Returns all addresses belonging to the currently authenticated user.",
        responses={200: AddressSerializer(many=True)},
        examples=[
            OpenApiExample(
                "Address List Example",
                value={
                    "id": 1,
                    "name": "Home",
                    "district": 4,
                    "region": 1,
                    "additional": "Near park",
                    "yandex_link": "https://yandex.uz/map",
                    "delivery_price": 15000.0,
                    "building": "12A",
                    "floor": 3,
                    "demophone_code": "12345",
                    "is_main": True,
                },
                response_only=True,
            )
        ],
    ),
    retrieve=extend_schema(
        summary="Get address by ID",
        description="Returns details of a single address object.",
        responses={200: AddressSerializer},
    ),
    create=extend_schema(
        summary="Create new address",
        description="Create a new address for the authenticated user. User is automatically assigned.",
        request=AddressSerializer,
        responses={201: AddressSerializer},
        examples=[
            OpenApiExample(
                "Create Address Example",
                value={
                    "name": "Work",
                    "district": 4,
                    "region": 1,
                    "additional": "Floor 2, Office 5",
                    "yandex_link": "https://yandex.uz/map",
                    "building": "25",
                    "floor": 2,
                    "demophone_code": "98765",
                    "is_main": False,
                },
            )
        ],
    ),
    update=extend_schema(
        summary="Update address",
        description="Update an existing address. Only non-primary addresses can be made non-primary.",
        request=AddressSerializer,
        responses={200: AddressSerializer},
    ),
    partial_update=extend_schema(
        summary="Partially update address",
        description="Partially update address fields.",
        request=AddressSerializer,
        responses={200: AddressSerializer},
    ),
    destroy=extend_schema(
        summary="Delete address",
        description="Delete an address by ID.",
        responses={204: None},
    ),
)
class AddressViewSet(viewsets.ModelViewSet):
    serializer_class = AddressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user).order_by(
            "-is_main", "-id"
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


@extend_schema(
    summary="Send phone change OTP",
    description="Send OTP for changing/verifying phone number",
    request=ChangePhoneSerializer,
    responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
    examples=[
        OpenApiExample(
            "Request Example",
            value={"phone": "+998901234567", "is_new": True},
            request_only=True,
        ),
        OpenApiExample(
            "Success Response",
            value={"message": "OTP sent successfully"},
            response_only=True,
            status_codes=["200"],
        ),
        OpenApiExample(
            "Active OTP Response",
            value={
                "message": "You already have an active OTP...",
                "remaining_time": 90,
                "phone": "+998901234567",
                "is_new": True,
            },
            response_only=True,
            status_codes=["200"],
        ),
    ],
    tags=["Phone Verification"],
)
class SendPhoneChangeOTPView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePhoneSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        is_new = serializer.validated_data["is_new"]
        user = request.user

        if is_new:
            phone = serializer.validated_data["phone"]
        else:
            phone = user.phone

        if not is_new and user.phone != phone:
            return Response(
                {
                    "error": _(
                        "Provided phone number doesn't match your current phone number"
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if is_new and User.objects.filter(phone=phone).exists():
            return Response(
                {"error": _("This phone number is already registered by another user")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        active_otp = OTP.objects.filter(
            phone=phone, is_used=False, expired_at__gt=timezone.now()
        ).first()

        if active_otp:
            remaining_time = (active_otp.expired_at - timezone.now()).seconds
            return Response(
                {
                    "message": _(
                        "You already have an active OTP that you can use. Please wait %(seconds) seconds before requesting a new one."
                    )
                    % {"seconds": remaining_time},
                    "remaining_time": remaining_time,
                    "phone": phone,
                    "is_new": is_new,
                },
                status=status.HTTP_200_OK,
            )

        code = str(random.randint(1_000, 9_999))

        otp, created = OTP.objects.update_or_create(
            phone=phone,
            defaults={
                "code": code,
                "is_used": False,
                "expired_at": timezone.now() + timedelta(minutes=3),
            },
        )
        send_sms.delay(
            phone,
            f"Carland tizimida telefon raqamingizni o'zgartirish uchun tasdiqlash kodi: {code}. Iltimos, ushbu kodni hech kimga bermang.",
        )

        return Response({"message": "OTP sent successfully"}, status=status.HTTP_200_OK)


@extend_schema(
    summary="Verify phone change OTP",
    description="Verify OTP for changing/verifying phone number",
    request=ChangePhoneVerifyOTPSerializer,
    responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
    examples=[
        OpenApiExample(
            "Request Example",
            value={"phone": "+998901234567", "code": "1234", "is_new": True},
            request_only=True,
        ),
        OpenApiExample(
            "Success Response (New Phone)",
            value={"message": "Phone number changed successfully"},
            response_only=True,
            status_codes=["200"],
        ),
        OpenApiExample(
            "Success Response (Verification)",
            value={"message": "Current phone number verified successfully"},
            response_only=True,
            status_codes=["200"],
        ),
    ],
    tags=["Phone Verification"],
)
class VerifyPhoneChangeOTPView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePhoneVerifyOTPSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        phone = serializer.validated_data["phone"]
        code = serializer.validated_data["code"]
        is_new = serializer.validated_data["is_new"]
        user = request.user

        try:
            otp = OTP.objects.get(phone=phone, code=code, is_used=False)

            if timezone.now() > otp.expired_at:
                return Response(
                    {"error": "OTP code has expired"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            otp.is_used = True
            otp.save()

            if not is_new:
                return Response(
                    {"message": _("Current phone number verified successfully")},
                    status=status.HTTP_200_OK,
                )

            user.phone = phone
            user.save()

            return Response(
                {"message": _("Phone number changed successfully")},
                status=status.HTTP_200_OK,
            )

        except OTP.DoesNotExist:
            return Response(
                {"error": _("Invalid OTP code or phone number")},
                status=status.HTTP_400_BAD_REQUEST,
            )


class UserShareInfoView(viewsets.ModelViewSet):
    queryset = UserShareInfo.objects.all()
    serializer_class = UserShareInfoSerializer
    # permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return UserShareInfo.objects.filter(user=self.request.user)
    
    
class CreateUserShareInfoView(APIView):
    # permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        operation_summary="Create user share info",
        operation_description="Create share information for the authenticated user.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "unique_code": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Unique code for sharing",
                ),
            },
            required=["unique_code"],
        ),
        responses={201: UserShareInfoSerializer, 400: OpenApiTypes.OBJECT},
        tags=["User Share Info"],
    )
    def post(self, request):
        serializer = UserShareInfoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
        
class NotificationMessagesViewSet(viewsets.ModelViewSet):
    queryset = NotificationMessages.objects.all()
    serializer_class = NotificationMessagesSerializer
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        return [IsAdminUser()]

class SendNotificationView(APIView):
    @swagger_auto_schema(
        operation_summary="Send custom notification",
        operation_description="Send a custom notification to a user based on a predefined message template.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "message_id": openapi.Schema(type=openapi.TYPE_INTEGER, description="ID of the notification message template"),
                "user_id": openapi.Schema(type=openapi.TYPE_INTEGER, description="ID of the user to send the notification to"),
            },
            required=["message_id", "user_id"],
        ),
        responses={
            200: openapi.Response(
                description="Notification sent successfully",
                examples={
                    "application/json": {"message": "Notification sent successfully"}
                },
            ),
            404: openapi.Response(
                description="Notification message or user not found",
                examples={
                    "application/json": {"error": "Notification message not found"}
                },
            ),
            400: openapi.Response(
                description="Bad request",
                examples={
                    "application/json": {"error": "Both message_id and user_id are required."}
                },
            ),
        },
    )
    def post(self, request):
        message_id = request.data.get("message_id")
        user_id = request.data.get("user_id")
        if not message_id or not user_id:
            return Response(
                {"error": "Both message_id and user_id are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            message = NotificationMessages.objects.get(id=message_id)
            user = UserInfo.objects.get(id=user_id)
            # Logic to send the notification to users goes here
            create_notification(
                content_object=None,
                notification_type='custom_message',
                title={
                    'uz': "Avto xabarnoma",
                    'ru': "Авто уведомление",
                    'en': "Auto Notification"
                },
                context=None,
                message={
                    'uz': message.message_uz,
                    'ru': message.message_ru,
                    'en': message.message_en
                },
                user=user,
            )
            return Response({"message": "Notification sent successfully"}, status=status.HTTP_200_OK)
        except NotificationMessages.DoesNotExist:
            return Response({"error": "Notification message not found"}, status=status.HTTP_404_NOT_FOUND)
