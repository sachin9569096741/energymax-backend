from uuid import uuid4
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, HttpUrl
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.affiliate.models.affiliate import Affiliate
from app.modules.affiliate.models.digilocker_verification import (
    DigiLockerVerification,
)
from app.modules.affiliate.security.dependencies import get_current_affiliate
from app.modules.affiliate.services.digilocker_service import (
    DigiLockerServiceError,
    digilocker_service,
)


router = APIRouter(
    prefix="/affiliate/kyc/digilocker",
    tags=["Affiliate - DigiLocker"],
)


class DigiLockerInitiateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    redirect_url: HttpUrl


def require_active_affiliate(affiliate: Affiliate) -> None:
    if str(affiliate.status).lower() != "active":
        raise HTTPException(
            status_code=403,
            detail="Your affiliate account is not active.",
        )


def get_owned_verification(
    db: Session,
    affiliate: Affiliate,
    verification_id: str,
) -> DigiLockerVerification:
    record = (
        db.query(DigiLockerVerification)
        .filter(
            DigiLockerVerification.verification_id == verification_id,
            DigiLockerVerification.affiliate_id == affiliate.id,
        )
        .first()
    )

    if record is None:
        raise HTTPException(
            status_code=404,
            detail="DigiLocker verification not found.",
        )

    return record


def translate_service_error(exc: DigiLockerServiceError) -> HTTPException:
    return HTTPException(
        status_code=exc.status_code,
        detail=exc.message,
    )


@router.post("/initiate")
async def initiate_digilocker(
    payload: DigiLockerInitiateRequest,
    affiliate: Affiliate = Depends(get_current_affiliate),
    db: Session = Depends(get_db),
):
    require_active_affiliate(affiliate)

    redirect_url = str(payload.redirect_url)

    # Require HTTPS outside local development.
    if urlparse(redirect_url).scheme.lower() != "https":
        raise HTTPException(
            status_code=400,
            detail="The DigiLocker redirect URL must use HTTPS.",
        )

    verification_id = f"aff_{uuid4().hex}"

    record = DigiLockerVerification(
        affiliate_id=affiliate.id,
        verification_id=verification_id,
        status="initiated",
        document_type="AADHAAR",
    )

    db.add(record)
    db.commit()
    db.refresh(record)

    try:
        result = await digilocker_service.create_link(
            verification_id=verification_id,
            redirect_url=redirect_url,
            user_flow="signin",
        )

        provider_reference_id = result.get("reference_id")
        if provider_reference_id:
            record.provider_reference_id = str(provider_reference_id)

        db.commit()

        verification_url = result.get("url")
        if not verification_url:
            raise DigiLockerServiceError(
                502,
                "The verification provider did not return a DigiLocker URL.",
            )

        return {
            "success": True,
            "verification_id": verification_id,
            "verification_public_id": record.public_id,
            "verification_url": verification_url,
            "expires_in_seconds": result.get("expires_in_seconds", 600),
            "message": "Redirect the affiliate to the verification URL.",
        }

    except DigiLockerServiceError as exc:
        record.status = "initiation_failed"
        db.commit()
        raise translate_service_error(exc) from exc

    except Exception:
        db.rollback()
        raise


@router.get("/status/{verification_id}")
async def get_digilocker_status(
    verification_id: str,
    affiliate: Affiliate = Depends(get_current_affiliate),
    db: Session = Depends(get_db),
):
    require_active_affiliate(affiliate)

    record = get_owned_verification(db, affiliate, verification_id)

    try:
        result = await digilocker_service.get_status(
            verification_id=record.verification_id,
        )

        # Provider response formats must be confirmed against your
        # Cashfree account's actual response before mapping final states.
        return {
            "success": True,
            "verification_id": record.verification_id,
            "local_status": record.status,
            "provider_response": result,
            "message": "verification status retrived successfully.",
        }

    except DigiLockerServiceError as exc:
        raise translate_service_error(exc) from exc


@router.get("/document/{verification_id}")
async def get_digilocker_document(
    verification_id: str,
    affiliate: Affiliate = Depends(get_current_affiliate),
    db: Session = Depends(get_db),
):
    require_active_affiliate(affiliate)

    record = get_owned_verification(db, affiliate, verification_id)

    # Fail closed until the provider's exact successful status is
    # confirmed and persisted by the status-verification implementation.
    if record.status.lower() not in {"verified", "success", "completed"}:
        raise HTTPException(
            status_code=409,
            detail="The DigiLocker verification has not been confirmed.",
        )

    try:
        result = await digilocker_service.get_document(
            verification_id=record.verification_id,
            document_type="AADHAAR",
        )

        return {
            "success": True,
            "verification_id": record.verification_id,
            "document": result,
        }

    except DigiLockerServiceError as exc:
        raise translate_service_error(exc) from exc