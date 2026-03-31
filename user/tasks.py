import os
import requests
import logging
from celery import shared_task
from django.contrib.contenttypes.models import ContentType
from .models import MessageLog

logger = logging.getLogger(__name__)


@shared_task
def send_sms(phone, message, content_type_id=None, object_id=None, message_type=None, context=None):
    FROM_SMS = "4546"
    LOGIN_URL = os.getenv("ESKIZ_LOGIN_URL")
    SMS_URL = os.getenv("ESKIZ_SMS_URL")
    SMS_EMAIL = os.getenv("SMS_EMAIL")
    SMS_PASSWORD = os.getenv("SMS_PASSWORD")

    logger.info(f"Starting SMS send task to {phone}")

    # Create log before sending
    message_log = MessageLog.objects.create(
        send_by="system",
        recipient=phone,
        content=message,
        content_type_id=content_type_id,
        object_id=object_id,
        message_type=message_type or "general",
        context=context,
    )

    login_payload = {"email": SMS_EMAIL, "password": SMS_PASSWORD}

    try:
        login_response = requests.post(url=LOGIN_URL, json=login_payload)
        login_response.raise_for_status()
        token = login_response.json().get("data", {}).get("token")

        if not token:
            raise ValueError("Eskiz token not found in response")

    except Exception as exc:
        logger.error(f"Eskiz auth failed: {exc}")
        message_log.status = MessageLog.MessageStatus.FAILED
        message_log.error_details = f"Token error: {exc}"
        message_log.save()
        return False

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    sms_payload = {"mobile_phone": phone, "message": message, "from": FROM_SMS}

    try:
        sms_response = requests.post(url=SMS_URL, headers=headers, json=sms_payload)
        sms_response.raise_for_status()
        logger.info(f"Eskiz SMS sent to {phone}: {sms_response.text}")

        message_log.status = MessageLog.MessageStatus.SENT
        message_log.save()
        return True

    except requests.exceptions.RequestException as exc:
        logger.error(f"SMS sending failed to {phone}: {exc}")
        message_log.status = MessageLog.MessageStatus.FAILED
        message_log.error_details = str(sms_response.text) if 'sms_response' in locals() else str(exc)
        message_log.save()
        return False
