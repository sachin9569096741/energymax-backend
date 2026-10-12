from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.modules.shop.customer.repositories.customer_auth import (
    CustomerAuthRepository,
)
from app.modules.shop.customer.security.security import hash_session_token
from app.modules.shop.customer.schemas.auth import (
    CustomerAuthResponse,
    CustomerLoginRequest,
    CustomerRegisterRequest,
    CustomerResponse,
    CustomerRegistrationResponse,
)
from app.modules.shop.customer.services.customer_email_verification import (
    CustomerEmailVerificationService,
)
from app.modules.shop.customer.services.customer_otp import CustomerOTPService
from app.modules.shop.customer.services.customer_auth import (
    CustomerAuthService,
)


router = APIRouter(
    prefix="/customer/auth",
    tags=["Shop - Customer Auth"],
)



@router.post(
    "/register",
    response_model=CustomerRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_customer(
    data: CustomerRegisterRequest,
    db: Session = Depends(get_db),
):
    repository = CustomerAuthRepository(db)
    auth_service = CustomerAuthService(repository)

    customer = auth_service.register(data)

    if not customer.email:
        db.rollback()
        raise HTTPException(
            status_code=422,
            detail="An email address is required to register.",
        )

    email_service = CustomerEmailVerificationService(repository)

    try:
        expires_at = email_service.send_verification_link(customer)

        db.commit()
        db.refresh(customer)

    except Exception:
        db.rollback()
        raise

    return CustomerRegistrationResponse(
        message=(
            "Registration successful. Please check your email "
            "and click the verification link to verify your account."
        ),
        customer=CustomerResponse.model_validate(customer),
        email=customer.email,
        verification_required=True,
        expires_at=expires_at,
    )



@router.post(
    "/login",
    response_model=CustomerAuthResponse,
)
def login_customer(
    data: CustomerLoginRequest,
    db: Session = Depends(get_db),
):
    repository = CustomerAuthRepository(db)
    service = CustomerAuthService(repository)

    customer, session_token = service.login(data)

    db.commit()
    db.refresh(customer)

    return CustomerAuthResponse(
        customer=CustomerResponse.model_validate(customer),
        session_token=session_token,
    )

@router.post("/logout")
def logout(
        x_customer_session_token: str | None = Header(
            default=None,
            alias="X-Customer-Session-Token",
        ),
        db: Session = Depends(get_db),
    ):
        if not x_customer_session_token:
            raise HTTPException(
                status_code=401,
                detail="Customer authentication required.",
            )

        repository = CustomerAuthRepository(db)

        token_hash = hash_session_token(x_customer_session_token)

        revoked = repository.revoke_session(token_hash)

        if not revoked:
            raise HTTPException(
                status_code=401,
                detail="Invalid customer session.",
            )

        db.commit()

        return {
            "message": "Customer logged out successfully."
        }


@router.post(
    "/verify-email",
    response_model=CustomerAuthResponse,
)
def verify_customer_email(
    token: str,
    db: Session = Depends(get_db),
):
    repository = CustomerAuthRepository(db)
    service = CustomerEmailVerificationService(repository)

    try:
        customer, session_token = service.verify_token(token)
        db.commit()
        db.refresh(customer)
    except Exception:
        db.rollback()
        raise

    return CustomerAuthResponse(
        customer=CustomerResponse.model_validate(customer),
        session_token=session_token,
    )

