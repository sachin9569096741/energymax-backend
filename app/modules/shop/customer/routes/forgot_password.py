from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.shop.customer.repositories.customer_auth import (
    CustomerAuthRepository,
)
from app.modules.shop.customer.schemas.auth import (
    ForgotPasswordConfirmOTPRequest,
    ForgotPasswordConfirmOTPResponse,
    ForgotPasswordOTPResponse,
    ForgotPasswordRequest,
    ForgotPasswordResetRequest,
)
from app.modules.shop.customer.services.forgot_password import (
    ForgotPasswordService,
    GENERIC_MESSAGE,
)

router = APIRouter(
    prefix="/customer/auth/forgot-password",
    tags=["Shop - Customer Password Recovery"],
)


@router.post("/verify", response_model=ForgotPasswordOTPResponse)
def request_password_reset_otp(
    data: ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    service = ForgotPasswordService(CustomerAuthRepository(db))

    try:
        service.request_otp(data.method, data.identifier)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return ForgotPasswordOTPResponse(message=GENERIC_MESSAGE)


@router.post("/resend", response_model=ForgotPasswordOTPResponse)
def resend_password_reset_otp(
    data: ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    service = ForgotPasswordService(CustomerAuthRepository(db))

    try:
        service.request_otp(data.method, data.identifier)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return ForgotPasswordOTPResponse(message=GENERIC_MESSAGE)


@router.post(
    "/confirm-otp",
    response_model=ForgotPasswordConfirmOTPResponse,
)
def confirm_password_reset_otp(
    data: ForgotPasswordConfirmOTPRequest,
    db: Session = Depends(get_db),
):
    service = ForgotPasswordService(CustomerAuthRepository(db))

    try:
        reset_token, expires_at = service.confirm_otp(
            data.method,
            data.identifier,
            data.code,
        )
        db.commit()
    except HTTPException:
        # Preserve failed-attempt counters on invalid OTPs.
        db.commit()
        raise
    except Exception:
        db.rollback()
        raise

    return ForgotPasswordConfirmOTPResponse(
        message="Recovery code verified. You may now set a new password.",
        reset_token=reset_token,
        expires_at=expires_at,
    )


@router.post("/reset")
def reset_customer_password(
    data: ForgotPasswordResetRequest,
    db: Session = Depends(get_db),
):
    service = ForgotPasswordService(CustomerAuthRepository(db))

    try:
        service.reset_password(
            data.reset_token,
            data.new_password,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    return {
        "message": (
            "Password reset successfully. "
            "Please log in with your new password."
        )
    }