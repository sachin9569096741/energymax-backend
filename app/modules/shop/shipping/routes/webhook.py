
import hashlib
import hmac
import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.modules.shop.payment.models.webhook_event import WebhookEvent
from app.modules.shop.payment.repositories.payment import PaymentRepository
from app.modules.shop.shipping.repositories.shipment import ShipmentRepository
from app.modules.shop.order.services.order import OrderService


router = APIRouter(tags=["Shipping Webhooks"])

PROVIDER = "shiprocket"

# Only map statuses we explicitly understand.
STATUS_MAP = {
    "6": ("SHIPPED", "shipped"),
    "42": ("PICKED UP", "shipped"),
    "18": ("IN TRANSIT", "shipped"),
    "17": ("OUT FOR DELIVERY", "out_for_delivery"),
    "7": ("DELIVERED", "delivered"),
}

STATUS_NAME_MAP = {
    "SHIPPED": "shipped",
    "PICKED UP": "shipped",
    "IN TRANSIT": "shipped",
    "OUT FOR DELIVERY": "out_for_delivery",
    "DELIVERED": "delivered",
}

ORDER_SEQUENCE = ["shipped", "out_for_delivery", "delivered"]


def _event_fingerprint(payload: dict[str, Any]) -> str:
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _get_tracking_status(payload: dict[str, Any]):
    status_id = str(
        payload.get("shipment_status_id")
        or payload.get("current_status_id")
        or ""
    ).strip()

    if status_id in STATUS_MAP:
        return STATUS_MAP[status_id]

    name = str(
        payload.get("shipment_status")
        or payload.get("current_status")
        or ""
    ).strip().upper()

    target = STATUS_NAME_MAP.get(name)
    if target:
        return name, target

    return name or "UNKNOWN", None


def _advance_order_status(order, target: str, db: Session) -> bool:
    """
    Advance only shipping-related states.
    Never downgrade an order or revive a cancelled/refunded order.
    """
    if target not in ORDER_SEQUENCE:
        return False

    current = order.status

    # Shipment tracking must not move an order that has not reached
    # the packed stage, or revive a cancelled/refunded order.
    if current not in ("packed", "shipped", "out_for_delivery", "delivered"):
        return False

    if current == "delivered":
        return False

    current_index = -1 if current == "packed" else ORDER_SEQUENCE.index(current)
    target_index = ORDER_SEQUENCE.index(target)

    if target_index <= current_index:
        return False

    service = OrderService(db)

    for next_status in ORDER_SEQUENCE[current_index + 1 : target_index + 1]:
        service.update_order_status(
            order=order,
            new_status=next_status,
            note=f"Shipping carrier update: {target.replace('_', ' ')}.",
            changed_by="system:shipping_webhook",
        )

    return True


@router.post("/webhooks/logistics")
def receive_shipping_update(
    payload: dict[str, Any],
    x_api_key: str | None = Header(default=None, alias="x-api-key"),
    db: Session = Depends(get_db),
):
    expected_secret = settings.shiprocket_webhook_secret

    if not expected_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Shipping webhook authentication is not configured.",
        )

    if not x_api_key or not hmac.compare_digest(
        x_api_key,
        expected_secret,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook credentials.",
        )

    awb = str(payload.get("awb") or payload.get("awb_code") or "").strip()
    if not awb:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook payload is missing the AWB.",
        )

    fingerprint = _event_fingerprint(payload)
    provider_status, target_order_status = _get_tracking_status(payload)

    event_type = (
        str(payload.get("current_status") or payload.get("shipment_status") or provider_status)
        .strip()[:100]
        or "UNKNOWN"
    )

    repository = PaymentRepository(db)

    event = WebhookEvent(
        public_id=str(uuid4()),
        provider=PROVIDER,
        event_id=fingerprint,
        event_type=event_type,
        status="received",
        payload=payload,
        signature=None,
    )

    created_event = repository.create_webhook_event_if_new(event)

    if created_event is None:
        existing = repository.get_webhook_event(
            provider=PROVIDER,
            event_id=fingerprint,
        )

        if existing and existing.status in ("processed", "ignored"):
            return {
                "ok": True,
                "result": "duplicate",
            }

        # A conflicting event ID without a terminal result must not
        # be processed concurrently a second time.
        return {
            "ok": True,
            "result": "already_received",
        }

    shipment_repository = ShipmentRepository(db)
    shipment = shipment_repository.get_by_awb(awb, for_update=True)

    if shipment is None:
        created_event.status = "ignored"
        created_event.error_message = "No shipment matches this AWB."
        created_event.processed_at = datetime.now(timezone.utc)

        return {
            "ok": True,
            "result": "unknown_awb",
        }

    # Keep the raw carrier status for shipment-level tracking.
    shipment.status = provider_status.lower().replace(" ", "_")

    order = shipment.order
    if order is None:
        created_event.status = "ignored"
        created_event.error_message = "Shipment has no associated order."
        created_event.processed_at = datetime.now(timezone.utc)

        return {
            "ok": True,
            "result": "shipment_has_no_order",
        }

    changed = False

    if target_order_status is not None:
        changed = _advance_order_status(
            order=order,
            target=target_order_status,
            db=db,
        )

    created_event.status = "processed" if changed else "ignored"
    created_event.processed_at = datetime.now(timezone.utc)

    if not changed:
        created_event.error_message = (
            "Tracking update recorded without an order-status transition."
        )

    db.flush()

    return {
        "ok": True,
        "result": "processed" if changed else "tracking_recorded",
        "order_status": order.status,
    }
