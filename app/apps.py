from django.apps import AppConfig


class AppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "app"

    def ready(self):
        from . import signals
        from config.firebase_config import initialize_firebase
        initialize_firebase()
