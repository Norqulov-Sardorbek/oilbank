import requests
import logging
import random
from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from app.models.card import Card, CardImages

User = get_user_model()
logger = logging.getLogger(__name__)


class MulticardService:
    """Service class for interacting with the Multicard API."""

    BASE_URL = settings.MULTICARD_BASE_URL
    APPLICATION_ID = settings.MULTICARD_APPLICATION_ID
    SECRET = settings.MULTICARD_SECRET
    STORE_ID = settings.MULTICARD_STORE_ID
    CALLBACK_URL = getattr(settings, "MULTICARD_CALLBACK_URL", None)
    REDIRECT_URL = settings.MULTICARD_REDIRECT_URL
    REDIRECT_DECLINE_URL = settings.MULTICARD_REDIRECT_DECLINE_URL
    DEFAULT_LANG = settings.MULTICARD_DEFAULT_LANG
    TOKEN_CACHE_KEY = "multicard_token"
    TOKEN_CACHE_TIMEOUT = 24 * 60 * 60  # 24 hours

    def __init__(self):
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _fetch_token(self):
        """Fetches a new token from the Multicard API."""
        url = f"{self.BASE_URL}/auth"
        payload = {"application_id": self.APPLICATION_ID, "secret": self.SECRET}
        logger.debug("Multicard auth request. URL: %s, Payload: %s", url, payload)
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            response.raise_for_status()
            token = response.json().get("token")
            if not token:
                logger.error("Token not found in Multicard response: %s", response.text)
                raise ValidationError("Token not found in response")
            logger.info("Successfully retrieved Multicard token")
            return token
        except requests.exceptions.RequestException as e:
            logger.error(
                "Multicard auth failed. Status code: %s, Response: %s",
                getattr(e.response, "status_code", "No status"),
                getattr(e.response, "text", "No text"),
            )
            raise ValidationError(f"Failed to get Multicard token: {str(e)}")

    def get_token(self):
        """Retrieves a token from Redis cache or requests a new one."""
        token = cache.get(self.TOKEN_CACHE_KEY)
        if not token:
            token = self._fetch_token()
            cache.set(self.TOKEN_CACHE_KEY, token, timeout=self.TOKEN_CACHE_TIMEOUT)
            logger.info(
                "Token cached in Redis for %s seconds", self.TOKEN_CACHE_TIMEOUT
            )
        return token

    def bind_card(self, user, pinfl=None, phone=None):
        """Creates a session for binding a card."""
        try:
            token = self.get_token()
            url = f"{self.BASE_URL}/payment/card/bind"
            payload = {
                "store_id": self.STORE_ID,
                "callback_url": self.CALLBACK_URL,
                "redirect_url": self.REDIRECT_URL,
                "redirect_decline_url": self.REDIRECT_DECLINE_URL,
                "payer_id": str(user.id),
                "lang": self.DEFAULT_LANG,
            }
            if pinfl:
                payload["pinfl"] = pinfl
            if phone:
                payload["phone"] = phone
            headers = {"Authorization": f"Bearer {token}", **self.headers}
            logger.debug("Binding card. URL: %s, Payload: %s", url, payload)
            response = requests.post(url, json=payload, headers=headers)
            if response.status_code == 200 and response.json().get("success"):
                data = response.json().get("data")
                return {
                    "success": True,
                    "session_id": data.get("session_id"),
                    "form_url": data.get("form_url"),
                }
            else:
                logger.error("Card binding failed: %s", response.text)
                return {
                    "success": False,
                    "error": response.json().get("error", response.text),
                }
        except Exception as e:
            logger.error(f"Error binding card: {str(e)}")
            return {"success": False, "error": str(e)}

    def handle_callback(self, data):
        """Processes the callback received from Multicard."""
        card_token = data.get("card_token")
        phone = data.get("phone")
        holder_name = data.get("holder_name")
        card_pan = data.get("card_pan")
        ps = data.get("ps")
        status_card = data.get("status")
        payer_id = data.get("payer_id")

        if not card_token:
            logger.error("Card token is missing in callback data")
            return {"success": False, "error": "Card token is required"}

        try:
            with transaction.atomic():
                user = (
                    User.objects.filter(id=int(payer_id)).first() if payer_id else None
                )
                if not user:
                    logger.error("User not found for payer_id: %s", payer_id)
                    return {"success": False, "error": "User not found"}

                # Tasodifiy background_image tanlash
                background_image = CardImages.objects.order_by("?").first()
                if not background_image:
                    logger.error("No background images available")
                    return {"success": False, "error": "No background images available"}

                card = Card.objects.create(
                    user=user,
                    card_token=card_token,
                    owner=holder_name or "Unknown",
                    card_name=f"{ps} Card",
                    card_number=card_pan,
                    phone_number=phone or "",
                    processing=ps or "unknown",
                    is_active=status_card == "active",
                    background_image=background_image,
                )
                logger.info("Card created successfully: %s", card_token)
                return {"success": True, "card_id": card.id}
        except Exception as e:
            logger.error(f"Error processing callback: {str(e)}")
            return {"success": False, "error": str(e)}

    def delete_card(self, user, card_token):
        """Deletes a card."""
        try:
            card = Card.objects.filter(user=user, card_token=card_token).first()
            if not card:
                logger.error("Card not found: %s", card_token)
                return {
                    "success": False,
                    "error": "Card not found or you don't have permission to delete it",
                }
            token = self.get_token()
            url = f"{self.BASE_URL}/payment/card/{card_token}"
            headers = {"Authorization": f"Bearer {token}", **self.headers}
            logger.debug("Deleting card. URL: %s", url)
            response = requests.delete(url, headers=headers)
            if response.status_code == 200 and response.json().get("success"):
                card.delete()
                logger.info("Card deleted successfully: %s", card_token)
                return {"success": True}
            else:
                logger.error("Card deletion failed: %s", response.text)
                return {
                    "success": False,
                    "error": response.json().get("error", response.text),
                }
        except Exception as e:
            logger.error(f"Error deleting card %s: {str(e)}", card_token)
            return {"success": False, "error": str(e)}
