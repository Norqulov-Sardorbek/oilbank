import json
import logging
from django.conf import settings

logger = logging.getLogger("utils.middlewares")
from django.http import (
    FileResponse,
    StreamingHttpResponse,
)


class IgnoreTokenOnLoginMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.exempt_paths = [
            "/user/token/",
            # '/user/token/refresh/',
            "/user/verify-otp/",
            "/user/send-otp/",
            "/api/company-benefit/",
            "/api/company-comment/",
            "/api/app-version-check/",
            "/api/branch/",
        ]

    def __call__(self, request):
        if request.path == "/user/profile/" and request.method == "POST":
            request.META.pop("HTTP_AUTHORIZATION", None)
            logger.debug(
                f"[Token Ignored] Authorization header removed for path: '{request.path}' and method: POST"
            )

        elif request.path in self.exempt_paths:
            request.META.pop("HTTP_AUTHORIZATION", None)
            logger.debug(
                f"[Token Ignored] Authorization header removed for path: '{request.path}'"
            )

        response = self.get_response(request)
        return response


class DevLoggerMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.exclude_paths = getattr(settings, "DEBUG_LOGGER_EXCLUDE_PATHS", [])
        self.max_length = getattr(settings, "DEBUG_LOG_MAX_LENGTH", 1000)

    def __call__(self, request):
        self._log_request(request)
        response = self.get_response(request)
        self._log_response(request, response)
        return response

    def _log_request(self, request):
        logger.debug(f"➡️  {request.method} {request.get_full_path()}")

        if request.body:
            try:
                parsed = json.loads(request.body)
                pretty = json.dumps(parsed, indent=4, ensure_ascii=False)
                logger.debug(f"📦 Request Body:\n{pretty}")
            except json.JSONDecodeError:
                logger.debug(f"📦 Raw Body: {request.body.decode(errors='ignore')}")
            except Exception as e:
                logger.debug(f"⚠️ Error parsing request body: {str(e)}")

    def _log_response(self, request, response):
        if any(request.path.startswith(path) for path in self.exclude_paths):
            return

        logger.debug(
            f"⬅️  Response {response.status_code} for {request.method} {request.get_full_path()}"
        )

        content_type = getattr(response, "content_type", None)
        if content_type:
            logger.debug(f"Content-Type: {content_type}")
        else:
            logger.debug("⚠️ Response has no content_type")

        try:
            if isinstance(response, (FileResponse, StreamingHttpResponse)):
                logger.debug("📤 Streaming or file response (not logged)")
                return

            content = getattr(response, "content", b"")
            if not content:
                logger.debug("📤 Empty response")
                return

            # JSON response
            if content_type == "application/json":
                try:
                    parsed = json.loads(content)
                    pretty = json.dumps(parsed, indent=4, ensure_ascii=False)
                    logger.debug(f"📤 JSON Response:\n{pretty}")
                except json.JSONDecodeError:
                    logger.debug(f"📤 Malformed JSON Response: {content[:200]}")
                return

            # Binary content
            if content_type and content_type.startswith(
                ("image/", "application/octet-stream")
            ):
                logger.debug("📤 Binary content (not logged)")
                return

            # Regular text response
            decoded = content.decode(errors="ignore")
            if len(decoded) > self.max_length:
                decoded = decoded[: self.max_length] + "... [TRUNCATED]"
            logger.debug(f"📤 Response Content:\n{decoded}")

        except Exception as e:
            logger.debug(f"⚠️ Error logging response: {str(e)}")
