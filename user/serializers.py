# utils
import datetime
import random


# global imports
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import serializers
from django.core.validators import RegexValidator
from django.utils import timezone
from django.conf import settings
from django.utils.translation import gettext_lazy as _


# local imports
from .models import User, UserInfo, OTP, Address, MessageLog, Referral,UserShareInfo
from .tasks import send_sms
from fcm_django.models import FCMDevice
import logging

logger = logging.getLogger(__name__)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "odoo_id",
            "sync_status",
            "phone",
            "role",
            "is_active",
            "is_staff",
            "is_superuser",
        ]


class UserInfoSerializer(serializers.ModelSerializer):
    phone = serializers.SerializerMethodField()
    registered_at = serializers.SerializerMethodField()

    class Meta:
        model = UserInfo
        fields = [
            "id",
            "user",
            "first_name",
            "last_name",
            "avatar",
            "address",
            "phone",
            "language",
            "birth_date",
            "gender",
            "registered_at",
            "referral_link",
            "referral_count"
        ]
        read_only_fields = ["user", "phone", "registered_at", "referral_count", "referral_link"]

    def get_phone(self, obj):
        """
        Getting user phone for UserInfo
        """
        return obj.user.phone

    def get_avatar(self, obj):
        request = self.context.get("request")
        if obj.avatar and hasattr(obj.avatar, "url"):
            return request.build_absolute_uri(obj.avatar.url)
        return None

    def get_registered_at(self, obj):
        """
        Getting user registered datetime from User model
        """
        return obj.user.created_at

    def create(self, validated_data):
        user = self.context.get("user")
        validated_data["user"] = user
        return super().create(validated_data)


class SendOTPSerializer(serializers.Serializer):
    phone_regex = RegexValidator(
        regex=r"^(\+998|998)\d{9}$",
        message="Phone number must be in correct format: +998XXXXXXXXX or 998XXXXXXXXX",
    )
    phone = serializers.CharField(max_length=20, validators=[phone_regex])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.purpose = self.context.get("purpose", "login")  # default to "login"

    def create(self, validated_data):
        phone = validated_data.get("phone")
        otp_unused = OTP.objects.filter(phone=phone).first()

        if otp_unused and otp_unused.expired_at > timezone.now():
            delta_seconds = int(
                (otp_unused.expired_at - timezone.now()).total_seconds()
            )
            if not otp_unused.is_used:
                return otp_unused, False, None
            else:
                return (
                    None,
                    None,
                    _(
                        "You have recently used an SMS code, please wait {seconds} seconds for a new one"
                    ).format(seconds=delta_seconds),
                )

        count_sms_last_24_hours = MessageLog.objects.filter(
            recipient=phone,
            status=MessageLog.MessageStatus.SENT,
            sent_at__gt=timezone.now() - datetime.timedelta(hours=24),
            message_type="general",
        ).count()
        message = MessageLog.objects.filter(
            recipient=phone,
            status=MessageLog.MessageStatus.SENT,
            sent_at__gt=timezone.now() - datetime.timedelta(hours=24),
            message_type="general",
        ).first()

        limit_last_24_hours = int(settings.SMS_LIMIT)

        if count_sms_last_24_hours >= limit_last_24_hours:
            if message:
                next_allowed_time = message.sent_at + datetime.timedelta(hours=24)
                time_remaining = next_allowed_time - timezone.now()
            else:
                time_remaining = datetime.timedelta(hours=24)

            return (
                None,
                None,
                _(
                    "You have exceeded the SMS limit for the last 24 hours. Please wait {hours} hours before sending another SMS"
                ).format(hours=int(time_remaining.total_seconds() // 3600 + 1)),
            )

        code = str(random.randint(1_000, 9_999))
        APP_SMS_HASH = getattr(settings, "APP_SMS_HASH", None)
        expired_at = timezone.now() + datetime.timedelta(seconds=90)

        otp, created = OTP.objects.update_or_create(
            phone=phone,
            defaults={"code": code, "expired_at": expired_at, "is_used": False},
        )

        if phone not in settings.TESTER_LOGINS:
            message_text = ""
            if self.purpose == "login":
                message_text = _(
                    "<#> Your verification code to access the Carland system is: {code}. Please do not share this code with anyone.\n\n{hash}"
                ).format(code=code, hash=APP_SMS_HASH)
            elif self.purpose == "delete":
                message_text = _(
                    "Code for deleting accounting data in the Carland.uz system: {code}"
                ).format(code=code)
            send_sms.delay(phone, message_text)

        return otp, True, None


class VerifyOTPSerializer(serializers.Serializer):
    phone_regex = RegexValidator(
        regex=r"^(\+998|998)\d{9}$",
        message="Phone number must be in correct format: +998XXXXXXXXX or 998XXXXXXXXX",
    )
    phone = serializers.CharField(
        max_length=20, validators=[phone_regex], required=True
    )
    code = serializers.CharField(max_length=6, required=True)
    registration_id = serializers.CharField(max_length=255, required=False, allow_blank=True, allow_null=True)
    device_type = serializers.ChoiceField(
        choices=['android', 'ios'], required=False, allow_blank=True, allow_null=True, default='ios'
    )
    referral_code = serializers.CharField(max_length=32, required=False, allow_blank=True, allow_null=True)

    def validate(self, attrs):
        from django.conf import settings
        phone = attrs["phone"]
        code = attrs["code"]
        
        if phone == "+998932848439" and code == "1111":
            return attrs  # Bypass for tester
        
        if phone in settings.TESTER_LOGINS and code == settings.TESTER_OTP:
            return attrs

        try:
            otp = OTP.objects.get(phone=phone)
        except OTP.DoesNotExist:
            raise serializers.ValidationError(
                {"phone": "OTP not found for this phone number."}
            )

        if otp.is_used:
            raise serializers.ValidationError(
                {"code": "OTP code has already been used."}
            )

        if timezone.now() > otp.expired_at:
            raise serializers.ValidationError({"code": _("OTP has expired.")})

        if otp.code != code:
            raise serializers.ValidationError({"code": _("Invalid OTP code.")})

        # Validate referral code if provided
        referral_code = attrs.get("referral_code")
        if referral_code:
            try:
                referrer_info = UserInfo.objects.get(referral_code=referral_code)
                attrs["referrer_user"] = referrer_info.user
            except UserInfo.DoesNotExist:
                raise serializers.ValidationError(
                    {"referral_code": "Invalid referral code."}
                )

        return attrs

    def create(self, validated_data):
        phone = validated_data.get("phone")
        registration_id = validated_data.get("registration_id", None)
        device_type = validated_data.get("device_type", "ios")
        referrer_user = validated_data.get("referrer_user", None)

        # Check if user exists
        user = User.objects.filter(phone=phone).first()
        created = False
      
        if not user:
            user = User(phone=phone)
            user.set_unusable_password()
            user.save()
            created = True

        # Mark OTP as used
        OTP.objects.filter(phone=phone).update(is_used=True)

        # Save FCM device token only if registration_id is provided and not empty
        if registration_id and registration_id.strip():
            try:
                device, device_created = FCMDevice.objects.get_or_create(
                    registration_id=registration_id,
                    defaults={
                        'user': user,
                        'type': device_type or 'android',
                        'active': True,
                    }
                )
                if not device_created:
                    device.user = user
                    device.type = device_type or device.type
                    device.active = True
                    device.save()
                device.subscribe_to_topic('global_notifications')
                device.subscribe_to_topic(f'user_{user.id}')
            except Exception as e:
                logger.error(f"Failed to register FCM device for user {user.id}: {e}")

        # Handle referral logic for new users
        if created and referrer_user:
            try:
                # Check if referral relationship already exists (shouldn't happen for new user, but safety check)
                referral, referral_created = Referral.objects.get_or_create(
                    referrer=referrer_user,
                    referred=user
                )
                
                if referral_created:
                    # Increment referrer's referral count
                    referrer_info = UserInfo.objects.get(user=referrer_user)
                    referrer_info.referral_count += 1
                    referrer_info.save(update_fields=['referral_count'])
                    
                    logger.info(f"New referral created: {referrer_user.phone} referred {user.phone}")
                
            except Exception as e:
                logger.error(f"Failed to process referral for user {user.id}: {e}")

        # Check if user info exists
        has_info = UserInfo.objects.filter(user=user).exists()
        
        if not created and has_info:
            refresh = RefreshToken.for_user(user)
            return {
                "user": user,
                "is_new": False,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            }
        else:
            return {"user": user, "is_new": True, "access": "", "refresh": ""}


class DeleteUserByPhoneOTPSerializer(serializers.Serializer):
    phone_regex = RegexValidator(
        regex=r"^(\+998|998)\d{9}$",
        message=_(
            "Phone number must be in correct format: +998XXXXXXXXX or 998XXXXXXXXX"
        ),
    )
    phone = serializers.CharField(
        max_length=20, validators=[phone_regex], required=True
    )
    code = serializers.CharField(max_length=6, required=True)

    def validate(self, attrs):
        phone = attrs["phone"]
        code = attrs["code"]

        # tester bypass
        if phone == "+998932848439" and code == "1111":
            return attrs

        try:
            otp = OTP.objects.get(phone=phone)
        except OTP.DoesNotExist:
            raise serializers.ValidationError(
                {"phone": _("OTP not found for this phone number.")}
            )

        if otp.is_used:
            raise serializers.ValidationError(
                {"code": _("OTP code has already been used.")}
            )

        if timezone.now() > otp.expired_at:
            raise serializers.ValidationError({"code": _("OTP has expired.")})

        if otp.code != code:
            raise serializers.ValidationError({"code": _("Invalid OTP code.")})

        return attrs

    def delete_user(self):
        phone = self.validated_data["phone"]
        user = User.objects.filter(phone=phone).first()

        if not user:
            raise serializers.ValidationError(
                {"phone": _("User with this phone number does not exist.")}
            )

        # delete user and related data
        UserInfo.objects.filter(user=user).delete()
        user.delete()

        # mark OTP as used
        OTP.objects.filter(phone=phone).update(is_used=True)

        return True


class AddressSerializer(serializers.ModelSerializer):
    delivery_price = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Address
        fields = [
            "id",
            "user",
            "name",
            "district",
            "region",
            "additional",
            "yandex_link",
            "delivery_price",
            "building",
            "floor",
            "demophone_code",
            "is_main",
        ]
        read_only_fields = ["user"]  # userni foydalanuvchidan so‘ramaslik uchun

    def get_delivery_price(self, instance):
        from app.models.order import DeliveryPrice

        delivery_price = DeliveryPrice.objects.filter(
            district=instance.district
        ).first()
        if delivery_price:
            return delivery_price.price
        return 0.00

    def create(self, validated_data):
        request = self.context.get("request")
        validated_data["user"] = request.user  # userni avtomatik biriktirish
        return super().create(validated_data)


class ChangePhoneSerializer(serializers.Serializer):
    phone_regex = RegexValidator(
        regex=r"^(\+998|998)\d{9}$",
        message="Phone number must be in correct format: +998XXXXXXXXX or 998XXXXXXXXX",
    )
    phone = serializers.CharField(max_length=20, validators=[phone_regex])
    is_new = serializers.BooleanField()


class ChangePhoneVerifyOTPSerializer(serializers.Serializer):
    phone_regex = RegexValidator(
        regex=r"^(\+998|998)\d{9}$",
        message="Phone number must be in correct format: +998XXXXXXXXX or 998XXXXXXXXX",
    )
    phone = serializers.CharField(max_length=20, validators=[phone_regex])
    code = serializers.CharField(max_length=6)
    is_new = serializers.BooleanField()



class UserShareInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserShareInfo
        fields = [
            "id",
            "user",
            "share_count",
            "last_shared_at",
        ]