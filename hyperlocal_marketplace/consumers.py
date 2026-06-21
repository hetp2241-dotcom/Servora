import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from .accounts.models import ChatMessage
from .accounts.notifications import create_notification_and_dispatch



class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        user = self.scope.get("user")

        self.partner_id = int(self.scope['url_route']['kwargs']['partner_id'])
        self.room_group_name = self._make_room_group_name(user.id, self.partner_id)

        if not user or user.is_anonymous:
            await self.close()
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        user = self.scope.get("user")
        if not user or user.is_anonymous:
            return

        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    @database_sync_to_async
    def _create_message(self, sender_id: int, receiver_id: int, message: str):
        return ChatMessage.objects.create(
            sender_id=sender_id,
            receiver_id=receiver_id,
            message=message,
        )

    @database_sync_to_async
    def _fetch_message_payload(self, chat_message: ChatMessage):
        return {
            "id": chat_message.id,
            "sender_id": chat_message.sender_id,
            "receiver_id": chat_message.receiver_id,
            "message": chat_message.message,
            "timestamp": chat_message.timestamp.isoformat(),
        }

    def _make_room_group_name(self, user_id: int, partner_id: int) -> str:
        # Stable room for a user <-> partner pair.
        # Sort IDs so both sides map to the same room name.
        a, b = sorted([int(user_id), int(partner_id)])
        return f"chat__{a}__{b}"

    @database_sync_to_async
    def _dispatch_new_message_notification(self, chat_message: ChatMessage):
        # Deterministic idempotency: one notification per chat message.
        recipient = chat_message.receiver
        actor = chat_message.sender
        create_notification_and_dispatch(
            recipient=recipient,
            actor=actor,
            type='NEW_MESSAGE',
            title='New message',
            message=chat_message.message[:200],
            link=f"/customer-dashboard/#chat-section",
            idempotency_key=f"NEW_MESSAGE:{chat_message.id}",
        )

    async def receive(self, text_data=None, bytes_data=None):

        if not text_data:
            return

        user = self.scope.get("user")
        if not user or user.is_anonymous:
            return

        try:
            payload = json.loads(text_data)
        except json.JSONDecodeError:
            return

        message_text = (payload.get("message") or "").strip()
        if not message_text:
            return

        chat_message = await self._create_message(
            sender_id=user.id,
            receiver_id=self.partner_id,
            message=message_text,
        )

        # NEW_MESSAGE notification MUST be created only here.
        await self._dispatch_new_message_notification(chat_message)

        message_payload = await self._fetch_message_payload(chat_message)





        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat.message",
                "message": message_payload,
            },
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({"type": "chat.message", "message": event["message"]}))

