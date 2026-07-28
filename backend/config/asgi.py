import os
import sys
import atexit
import logging
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

from django.core.asgi import get_asgi_application
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from surveillance.routing import websocket_urlpatterns

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})


def _shutdown_engine():
    try:
        from surveillance.ai.engine_instance import get_engine, clear_engine
        engine = get_engine()
        if engine and engine.is_running:
            engine.stop()
            clear_engine()
    except Exception:
        pass


atexit.register(_shutdown_engine)
