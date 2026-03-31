# serializers.py
from rest_framework import serializers


class AppVersionRequestSerializer(serializers.Serializer):
    app_version = serializers.CharField(
        help_text="Semantic‑version string of the client’s app, e.g. '2.3.1'"
    )


class AppVersionResponseSerializer(serializers.Serializer):
    is_latest = serializers.BooleanField(help_text="True if the client is up‑to‑date")
    store_version = serializers.CharField(help_text="Latest version found in the store")
    client_version = serializers.CharField(help_text="Version sent by the client")


class ErrorResponseSerializer(serializers.Serializer):
    error = serializers.CharField()
