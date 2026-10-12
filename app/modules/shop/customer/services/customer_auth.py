
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import HTTPException, status

from app.modules.shop.customer.models.customer import Customer
from app.modules.shop.customer.models.customer_session import CustomerSession
from app.modules.shop.customer.repositories.customer_auth import (
    CustomerAuthRepository,
)
from app.modules.shop.customer.schemas.auth import (
    CustomerLoginRequest,
    CustomerRegisterRequest,
)
from app.modules.shop.customer.security.security import (
    generate_session_token,
    hash_password,
    hash_session_token,
    verify_password,
)


CUSTOMER_SESSION_DAYS = 30


class CustomerAuthService:
    def __init__(self, repository: CustomerAuthRepository):
        self.repository = repository

    def register(
        self,
        data: CustomerRegisterRequest,
    ) -> Customer:
        username = data.username.strip()
        email = data.email.lower().strip() if data.email else None
        phone = data.phone.strip() if data.phone else None

        # Email verification is mandatory for registration.
        if not email:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="An email address is required to register.",
            )

        if self.repository.get_customer_by_username(username):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username is already registered.",
            )

        if self.repository.get_customer_by_email(email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email is already registered.",
            )

        if phone and self.repository.get_customer_by_phone(phone):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Phone number is already registered.",
            )

        customer = Customer(
            public_id=str(uuid4()),
            username=username,
            first_name=data.first_name.strip(),
            last_name=data.last_name.strip() if data.last_name else None,
            email=email,
            phone=phone,
            password_hash=hash_password(data.password),
            email_verified=False,
            phone_verified=False,
            is_active=True,
        )

        self.repository.create_customer(customer)

        # Do not create a session until the email is verified.
        return customer

    def login(
        self,
        data: CustomerLoginRequest,
    ) -> tuple[Customer, str]:
        identifier = data.identifier.strip()

        if "@" in identifier:
            identifier = identifier.lower()

        customer = self.repository.get_customer_by_identifier(identifier)

        if customer is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials.",
            )

        if not customer.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Customer account is inactive.",
            )

        if not customer.password_hash or not verify_password(
            data.password,
            customer.password_hash,
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials.",
            )

        if not customer.email_verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Please verify your email before logging in.",
            )

        customer.last_login_at = datetime.now(timezone.utc)
        session_token = self._create_session(customer)

        return customer, session_token

    def _create_session(self, customer: Customer) -> str:
        session_token = generate_session_token()
        token_hash = hash_session_token(session_token)

        expires_at = datetime.now(timezone.utc) + timedelta(
            days=CUSTOMER_SESSION_DAYS
        )

        session = CustomerSession(
            public_id=str(uuid4()),
            customer_id=customer.id,
            token_hash=token_hash,
            expires_at=expires_at,
            is_active=True,
        )

        self.repository.create_session(session)

        return session_token
