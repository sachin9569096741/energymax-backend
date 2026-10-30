import logging

from sqlalchemy.orm import Session

from app.modules.affiliate.models.digilocker_verification import (
    DigiLockerVerification,
)

logger = logging.getLogger(__name__)


class DigiLockerWebhookService:

    @staticmethod
    def find_verification(
        db: Session,
        verification_id: str,
    ) -> DigiLockerVerification | None:
        return (
            db.query(DigiLockerVerification)
            .filter(
                DigiLockerVerification.verification_id
                == verification_id
            )
            .first()
        )


digilocker_webhook_service = DigiLockerWebhookService()