from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException

from app.db.session import get_db
from app.modules.shop.customer.repositories.customer_auth import (
    CustomerAuthRepository,
)
from app.modules.shop.customer.schemas.auth import (
    CustomerOTPRequest,
    CustomerOTPResponse,
    CustomerOTPVerifyRequest,
    CustomerAuthResponse,
)
from app.modules.shop.customer.services.customer_otp import CustomerOTPService


router = APIRouter(
    prefix="/customer/auth/otp",
    tags=["Shop - Customer OTP"],
)


@router.post(
    "/request",
    response_model=CustomerOTPResponse,
)
def request_otp(
    data: CustomerOTPRequest,
    db: Session = Depends(get_db),
):
    repository = CustomerAuthRepository(db)
    service = CustomerOTPService(repository)

    expires_at, _otp_code = service.request_otp(
        destination=data.destination,
        channel=data.channel,
        purpose=data.purpose,
    )

    db.commit()

    return CustomerOTPResponse(
        message="OTP sent successfully.",
        expires_at=expires_at,
    )


@router.post(
    "/verify",
    response_model=CustomerAuthResponse,
)
def verify_otp(
    data: CustomerOTPVerifyRequest,
    db: Session = Depends(get_db),
):
    repository = CustomerAuthRepository(db)
    service = CustomerOTPService(repository)

    customer, session_token = service.verify_otp(
        destination=data.destination,
        channel=data.channel,
        purpose=data.purpose,
        code=data.code,
    )

    db.commit()

    if customer is None or session_token is None:
        raise HTTPException(
            status_code=400,
            detail="OTP verification did not create a customer session.",
        )

    return CustomerAuthResponse(
        customer=customer,
        session_token=session_token,
    )