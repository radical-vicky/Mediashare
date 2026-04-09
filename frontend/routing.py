# frontend/routing.py
from django.urls import re_path, path
from . import consumers

websocket_urlpatterns = [
    path('ws/call/<str:room_name>/', consumers.CallConsumer.as_asgi()),
]