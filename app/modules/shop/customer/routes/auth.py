from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from fastapi import Depends, Header, HTTPException
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
)
from app.modules.shop.customer.services.customer_auth import (
    CustomerAuthService,
)


router = APIRouter(
    prefix="/customer/auth",
    tags=["Shop - Customer Auth"],
)


@router.post(
    "/register",
    response_model=CustomerAuthResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_customer(
    data: CustomerRegisterRequest,
    db: Session = Depends(get_db),
):
    repository = CustomerAuthRepository(db)
    service = CustomerAuthService(repository)

    customer, session_token = service.register(data)

    db.commit()
    db.refresh(customer)

    return CustomerAuthResponse(
        customer=CustomerResponse.model_validate(customer),
        session_token=session_token,
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
