import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from .accounts.models import Notification


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if not user or user.is_anonymous:
            await self.close()
            return

        self.recipient_id = int(user.id)
        self.group_name = f"user__{self.recipient_id}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        user = self.scope.get("user")
        if not user or user.is_anonymous:
            return

        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    @database_sync_to_async
    def _latest_notifications_payload(self, limit: int = 20):
        qs = (
            Notification.objects.filter(recipient_id=self.recipient_id)
            .order_by("-created_at")[:limit]
        )
        return [
            {
                "id": n.id,
                "type": n.type,
                "title": n.title,
                "message": n.message,
                "link": n.link,
                "created_at": n.created_at.isoformat(),
                "read_at": n.read_at.isoformat() if n.read_at else None,
            }
            for n in qs
        ]

    async def receive(self, text_data=None, bytes_data=None):
        # Client can request latest notifications / unread counts.
        if not text_data:
            return

        user = self.scope.get("user")
        if not user or user.is_anonymous:
            return

        try:
            payload = json.loads(text_data)
        except json.JSONDecodeError:
            return

        action = payload.get("action")
        if action == "get_latest":
            latest = await self._latest_notifications_payload(limit=20)
            await self.send(
                text_data=json.dumps({
                    "type": "notifications.latest",
                    "notifications": latest,
                })
            )

    async def notification_event(self, event):
        await self.send(text_data=json.dumps({"type": "notifications.new", "notification": event["notification"]}))

