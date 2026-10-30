import json
import logging

from fastapi import APIRouter, Request

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/affiliate/kyc/digilocker",
    tags=["Affiliate - DigiLocker Webhooks"],
)


@router.post("/webhook")
async def digilocker_webhook(request: Request):
    """
    Receive Cashfree webhook requests.

    This endpoint is currently in integration-testing mode.
    It does not update KYC status.
    """

    try:
        raw_body = await request.body()

        if not raw_body:
            logger.info(
                "DigiLocker webhook endpoint connectivity test received."
            )

            return {
                "received": True,
                "processed": False,
                "message": "Webhook endpoint is reachable.",
            }

        try:
            payload = json.loads(raw_body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {
                "received": True,
                "processed": False,
                "message": "Webhook received; JSON parsing failed.",
            }

        if not isinstance(payload, dict):
            return {
                "received": True,
                "processed": False,
                "message": "Webhook received; expected a JSON object.",
            }

        event_type = (
            payload.get("type")
            or payload.get("event")
            or "unknown"
        )

        logger.info(
            "DigiLocker webhook received; event_type=%s",
            str(event_type)[:100],
        )

        # Do not trust or process events until Cashfree's
        # webhook authentication and event schema are verified.
        return {
            "received": True,
            "processed": False,
            "message": (
                "Webhook received. Authentication and event "
                "validation are required before processing."
            ),
        }

    except Exception:
        logger.exception("DigiLocker webhook request failed.")
        raise