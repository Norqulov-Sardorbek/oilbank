# your_app/utils.py
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework.views import exception_handler
from django.core.exceptions import ObjectDoesNotExist
from rest_framework.response import Response
from rest_framework import status
from django.utils.translation import gettext_lazy as _


def custom_jwt_exception_handler(exc, context):
    if isinstance(exc, (InvalidToken, TokenError, ObjectDoesNotExist)):
        return Response(
            {"error": _("Invalid token or user does not exist")},
            status=status.HTTP_401_UNAUTHORIZED,
        )
    return exception_handler(exc, context)
