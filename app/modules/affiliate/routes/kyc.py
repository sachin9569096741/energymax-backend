from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from app.db.session import get_db
from app.modules.affiliate.models.affiliate import Affiliate
from app.modules.affiliate.security.dependencies import get_current_affiliate
from app.modules.affiliate.services.kyc_service import (
    KYCServiceError,
    kyc_service,
)


router = APIRouter(
    prefix="/affiliate/kyc",
    tags=["Affiliate - KYC"],
)


class PANVerificationRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    pan: str = Field(
        ...,
        min_length=10,
        max_length=10,
        description="Affiliate's PAN number",
        examples=["ABCDE1234F"],
    )

    name: str | None = Field(
        default=None,
        max_length=200,
        description="Name associated with the PAN",
    )

class AadhaarOTPRequest(BaseModel):
    aadhaar_number: str = Field(
        ...,
        min_length=12,
        max_length=12,
        pattern=r"^[0-9]{12}$",
    )


class AadhaarOTPVerifyRequest(BaseModel):
    reference_id: str = Field(
        ...,
        min_length=1,
        max_length=200,
    )
    otp: str = Field(
        ...,
        min_length=6,
        max_length=6,
        pattern=r"^[0-9]{6}$",
    )


@router.post("/pan/verify")
async def verify_pan(
    payload: PANVerificationRequest,
    affiliate: Affiliate = Depends(get_current_affiliate),
    db: Session = Depends(get_db),
):
    """
    Verify the authenticated affiliate's PAN using Cashfree Secure ID.
    """

    # Ensure the authenticated affiliate is still an active account.
    if str(affiliate.status).lower() != "active":
        raise HTTPException(
            status_code=403,
            detail="Your affiliate account is not active.",
        )

    try:
        result = await kyc_service.verify_pan(
            pan=payload.pan,
            name=payload.name,
        )

        # Do not return the complete provider response because it may
        # contain personal information that should not be exposed.
        return {
            "success": True,
            "affiliate_id": affiliate.public_id,
            "document_type": result["document_type"],
            "masked_pan": result["masked_pan"],
            "verified": result["verified"],
            "provider_status": result["provider_status"],
            "message": result["message"],
        }

    except KYCServiceError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.message,
        ) from exc


@router.post("/aadhaar/otp")
async def generate_aadhaar_otp(
    payload: AadhaarOTPRequest,
    affiliate: Affiliate = Depends(get_current_affiliate),
):
    try:
        if not getattr(affiliate, "is_active", True):
            raise HTTPException(
                status_code=403,
                detail="Affiliate account is inactive.",
            )

        return await kyc_service.send_aadhaar_otp(
            payload.aadhaar_number
        )

    except KYCServiceError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.message,
        ) from exc



@router.post("/aadhaar/verify")
async def verify_aadhaar_otp(
    payload: AadhaarOTPVerifyRequest,
    affiliate: Affiliate = Depends(get_current_affiliate),
):
    try:
        if not getattr(affiliate, "is_active", True):
            raise HTTPException(
                status_code=403,
                detail="Affiliate account is inactive.",
            )

        return await kyc_service.verify_aadhaar_otp(
            reference_id=payload.reference_id,
            otp=payload.otp,
        )

    except KYCServiceError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.message,
        ) from exc