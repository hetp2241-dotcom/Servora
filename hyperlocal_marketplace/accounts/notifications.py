import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import Notification

logger = logging.getLogger(__name__)


def _recipient_group(recipient_id: int) -> str:
    return f"user__{int(recipient_id)}"


def create_notification_and_dispatch(
    *,
    recipient,
    actor,
    type: str,
    title: str,
    message: str,
    link: str,
    idempotency_key: str,
):
    """Create a notification (idempotent) and dispatch realtime event."""

    # Ensure we never double-create.

    try:
        with transaction.atomic():
            notification, created = Notification.objects.get_or_create(
                idempotency_key=idempotency_key,
                defaults={
                    "recipient": recipient,
                    "actor": actor,
                    "type": type,
                    "title": title,
                    "message": message,
                    "link": link,
                    "created_at": timezone.now(),
                },
            )
    except IntegrityError:
        # Unique constraint race.
        notification = Notification.objects.get(idempotency_key=idempotency_key)
        created = False

    # Always dispatch only if newly created.
    if not created:
        return notification

    channel_layer = get_channel_layer()
    if not channel_layer:
        return notification

    payload = {
        "id": notification.id,
        "type": notification.type,
        "title": notification.title,
        "message": notification.message,
        "link": notification.link,
        "created_at": notification.created_at.isoformat(),
        "read_at": notification.read_at.isoformat() if notification.read_at else None,
    }

    async_to_sync(channel_layer.group_send)(
        _recipient_group(notification.recipient_id),
        {
            "type": "notification_event",
            "notification": payload,
        },
    )

    return notification

