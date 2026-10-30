import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.affiliate.services.digilocker_webhook_service import (
    digilocker_webhook_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/affiliate/kyc/digilocker",
    tags=["Affiliate - DigiLocker Webhooks"],
)


class DigiLockerWebhookPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    type: str
    verification_id: str
    status: str | None = None
    event: str | None = None


@router.post("/webhook")
async def digilocker_webhook(
    payload: DigiLockerWebhookPayload,
    db: Session = Depends(get_db),
):
    event_type = payload.type or payload.event or "unknown"

    logger.info(
        "DigiLocker webhook received; event_type=%s",
        event_type[:100],
    )

    # This lookup is for integration development only.
    # The event is not trusted until Cashfree authentication is verified.
    record = digilocker_webhook_service.find_verification(
        db=db,
        verification_id=payload.verification_id,
    )

    if record is None:
        raise HTTPException(
            status_code=404,
            detail="DigiLocker verification record not found.",
        )

    return {
        "received": True,
        "processed": False,
        "verification_id": record.verification_id,
        "local_status": record.status,
        "message": (
            "Verification record found. Cashfree webhook authentication "
            "and event mapping are still required."
        ),
    }