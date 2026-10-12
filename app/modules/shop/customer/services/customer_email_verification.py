
import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import HTTPException

from app.core.email import EmailService
from app.core.config import settings
from app.modules.shop.customer.models.customer_email_verification import (
    CustomerEmailVerification,
)
from app.modules.shop.customer.models.customer_session import CustomerSession
from app.modules.shop.customer.repositories.customer_auth import (
    CustomerAuthRepository,
)
from app.modules.shop.customer.security.security import (
    generate_session_token,
    hash_session_token,
)
from app.modules.shop.customer.services.email_templates import (
    build_customer_verification_link_email,
)

logger = logging.getLogger(__name__)

VERIFICATION_EXPIRY_MINUTES = 10
CUSTOMER_SESSION_DAYS = 30


class CustomerEmailVerificationService:
    def __init__(self, repository: CustomerAuthRepository):
        self.repository = repository
        self.email_service = EmailService()

    def send_verification_link(self, customer) -> datetime:
        if not customer.email:
            raise HTTPException(
                status_code=422,
                detail="An email address is required.",
            )

        if not customer.is_active:
            raise HTTPException(
                status_code=403,
                detail="Customer account is inactive.",
            )

        if customer.email_verified:
            raise HTTPException(
                status_code=409,
                detail="This email address is already verified.",
            )

        now = datetime.now(timezone.utc)
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(
            raw_token.encode("utf-8")
        ).hexdigest()
        expires_at = now + timedelta(
            minutes=VERIFICATION_EXPIRY_MINUTES
        )

        self.repository.invalidate_email_verifications(customer.id)

        verification = CustomerEmailVerification(
            public_id=str(uuid4()),
            customer_id=customer.id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self.repository.create_email_verification(verification)

        base_url = settings.frontend_base_url.rstrip("/")
        verification_url = (
            f"{base_url}/verify-email?token={raw_token}"
        )

        html = build_customer_verification_link_email(
            verification_url
        )

        try:
            self.email_service.send_email(
                to=customer.email,
                subject="Verify your EnergyMaxGroup email",
                html=html,
            )
        except Exception:
            logger.exception("Failed to send customer verification link")
            raise HTTPException(
                status_code=502,
                detail="Unable to send verification email. Please try again.",
            )

        return expires_at

    def verify_token(self, raw_token: str):
        if not raw_token or len(raw_token) > 256:
            raise HTTPException(
                status_code=400,
                detail="Invalid or expired verification link.",
            )

        token_hash = hashlib.sha256(
            raw_token.encode("utf-8")
        ).hexdigest()

        verification = self.repository.get_email_verification_by_hash(
            token_hash
        )

        if verification is None or verification.used_at is not None:
            raise HTTPException(
                status_code=400,
                detail="Invalid or expired verification link.",
            )

        now = datetime.now(timezone.utc)
        expires_at = verification.expires_at

        # Some databases return naive datetimes even for timezone-aware columns.
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if expires_at <= now:
            raise HTTPException(
                status_code=400,
                detail="Invalid or expired verification link.",
            )

        customer = self.repository.get_customer_by_id(
            verification.customer_id
        )

        if customer is None or not customer.is_active:
            raise HTTPException(
                status_code=403,
                detail="Customer account is unavailable.",
            )

        if not customer.email:
            raise HTTPException(
                status_code=400,
                detail="Customer email address is missing.",
            )

        verification.used_at = now
        customer.email_verified = True
        customer.last_login_at = now

        session_token = generate_session_token()
        session = CustomerSession(
            public_id=str(uuid4()),
            customer_id=customer.id,
            token_hash=hash_session_token(session_token),
            expires_at=now + timedelta(days=CUSTOMER_SESSION_DAYS),
            is_active=True,
        )
        self.repository.create_session(session)
        self.repository.save()

        return customer, session_token
