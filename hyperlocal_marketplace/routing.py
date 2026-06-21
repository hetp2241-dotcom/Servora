from django.urls import re_path

from .consumers import ChatConsumer
from .notifications_consumers import NotificationConsumer

websocket_urlpatterns = [
    # partner_id comes from the querystring in the existing UI (?chat_with=ID)
    re_path(r"^ws/chat/(?P<partner_id>\d+)/$", ChatConsumer.as_asgi()),
    re_path(r"^ws/notifications/$", NotificationConsumer.as_asgi()),
]



