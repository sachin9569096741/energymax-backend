import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from app.core.realtime.websocket_manager import websocket_manager

logger = logging.getLogger(__name__)


def _json_safe(value: Any) -> Any:
    """Convert common Python values into JSON-compatible values."""

    if isinstance(value, (datetime, date)):
        return value.isoformat()

    if isinstance(value, (Decimal, UUID)):
        return str(value)

    if isinstance(value, dict):
        return {
            str(key): _json_safe(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]

    return value


def serialize_admin_notification(notification: Any) -> dict:
    """Serialize a persisted admin notification for WebSocket delivery."""

    return {
        "event": "notification.created",
        "notification": {
            "public_id": str(notification.public_id),
            "notification_type": notification.notification_type,
            "title": notification.title,
            "message": notification.message,
            "entity_type": notification.entity_type,
            "entity_public_id": notification.entity_public_id,
            "data": _json_safe(notification.data or {}),
            "is_read": bool(notification.is_read),
            "created_at": _json_safe(notification.created_at),
        },
    }


async def dispatch_admin_notification_payload(
    *,
    admin_user_id: int,
    payload: dict,
) -> bool:
    """
    Deliver an already-serialized notification to a connected admin.

    Delivery failures must not undo a committed business transaction.
    """

    try:
        return await websocket_manager.send_to_user(
            audience="admin",
            user_id=admin_user_id,
            message=payload,
        )
    except Exception:
        logger.exception(
            "WebSocket notification delivery failed for admin_user_id=%s",
            admin_user_id,
        )
        return False


async def dispatch_admin_notification(
    *,
    admin_user_id: int,
    notification: Any,
) -> bool:
    """Serialize and deliver an admin notification."""

    try:
        payload = serialize_admin_notification(notification)

        return await dispatch_admin_notification_payload(
            admin_user_id=admin_user_id,
            payload=payload,
        )
    except Exception:
        logger.exception(
            "Could not dispatch notification for admin_user_id=%s",
            admin_user_id,
        )
        return False