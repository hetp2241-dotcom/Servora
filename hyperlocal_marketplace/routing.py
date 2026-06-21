from django.urls import re_path

from .consumers import ChatConsumer

websocket_urlpatterns = [
    # partner_id comes from the querystring in the existing UI (?chat_with=ID)
    re_path(r"^ws/chat/(?P<partner_id>\d+)/$", ChatConsumer.as_asgi()),
]

