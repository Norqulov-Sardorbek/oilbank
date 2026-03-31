import os
from django.core.asgi import get_asgi_application
from django.utils.module_loading import import_string
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = ProtocolTypeRouter({
    'http': get_asgi_application(),
    'websocket': AuthMiddlewareStack(
        URLRouter(
            import_string('app.routing.websocket_urlpatterns')
        )
    ),
})