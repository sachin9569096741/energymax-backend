import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import HTTPException

from app.core.email import EmailService
from app.modules.shop.customer.models.customer_otp import CustomerOTP
from app.modules.shop.customer.repositories.customer_auth import (
    CustomerAuthRepository,
)
from app.modules.shop.customer.security.security import hash_password
from app.modules.shop.customer.services.email_templates import (
    build_customer_otp_email,
)

logger = logging.getLogger(__name__)

OTP_EXPIRY_MINUTES = 10
RESET_TOKEN_EXPIRY_MINUTES = 10
OTP_MAX_ATTEMPTS = 5
RESEND_COOLDOWN_SECONDS = 10

GENERIC_MESSAGE = (
    "If an account matches those details, a recovery code will be sent "
    "to its registered email address."
)


class ForgotPasswordService:
    def __init__(self, repository: CustomerAuthRepository):
        self.repository = repository
        self.email_service = EmailService()

    @staticmethod
    def _hash(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _normalize(method: str, identifier: str) -> str:
        identifier = identifier.strip()

        if method == "email":
            return identifier.lower()

        if method == "phone":
            return (
                identifier.replace(" ", "")
                .replace("-", "")
                .replace("(", "")
                .replace(")", "")
            )

        return identifier

    def _find_customer(self, method: str, identifier: str):
        if method == "username":
            return self.repository.get_customer_by_username(identifier)

        if method == "email":
            return self.repository.get_customer_by_email(identifier)

        return self.repository.get_customer_by_phone(identifier)

    def request_otp(self, method: str, identifier: str) -> None:
        method = method.strip().lower()

        if method not in {"username", "email", "phone"}:
            raise HTTPException(
                status_code=400,
                detail="Method must be username, email, or phone.",
            )

        identifier = self._normalize(method, identifier)
        customer = self._find_customer(method, identifier)

        # Do not disclose whether an account exists.
        if customer is None or not customer.is_active or not customer.email:
            return

        now = self._now()
        destination = customer.email.strip().lower()

        latest = self.repository.get_latest_otp(
            destination=destination,
            channel="email",
            purpose="password_reset",
        )

        if latest is not None:
            created_at = latest.created_at

            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)

            elapsed = (now - created_at).total_seconds()

            if elapsed < RESEND_COOLDOWN_SECONDS:
                # Return the same public response during the cooldown.
                return

        # Invalidate previous recovery codes and reset grants.
        self.repository.invalidate_password_reset_records(customer.id)

        code = f"{secrets.randbelow(1_000_000):06d}"
        expires_at = now + timedelta(minutes=OTP_EXPIRY_MINUTES)

        otp = CustomerOTP(
            public_id=str(uuid4()),
            customer_id=customer.id,
            channel="email",
            destination=destination,
            purpose="password_reset",
            code_hash=self._hash(code),
            expires_at=expires_at,
            attempts=0,
            max_attempts=OTP_MAX_ATTEMPTS,
        )

        self.repository.create_otp(otp)

        # Always send to the email already stored on the account.
        self.email_service.send_email(
            to=destination,
            subject="Reset your EnergyMax password",
            html=build_customer_otp_email(code),
        )

        logger.info("Password recovery OTP requested")

    def confirm_otp(
        self,
        method: str,
        identifier: str,
        code: str,
    ) -> tuple[str, datetime]:
        method = method.strip().lower()

        if method not in {"username", "email", "phone"}:
            raise HTTPException(
                status_code=400,
                detail="Method must be username, email, or phone.",
            )

        identifier = self._normalize(method, identifier)
        customer = self._find_customer(method, identifier)

        if customer is None or not customer.is_active or not customer.email:
            raise HTTPException(
                status_code=400,
                detail="Invalid or expired recovery code.",
            )

        destination = customer.email.strip().lower()

        otp = self.repository.get_latest_otp(
            destination=destination,
            channel="email",
            purpose="password_reset",
        )

        now = self._now()

        if (
            otp is None
            or otp.customer_id != customer.id
            or otp.consumed_at is not None
        ):
            raise HTTPException(
                status_code=400,
                detail="Invalid or expired recovery code.",
            )

        expires_at = otp.expires_at

        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if expires_at <= now:
            raise HTTPException(
                status_code=400,
                detail="Invalid or expired recovery code.",
            )

        if otp.attempts >= otp.max_attempts:
            raise HTTPException(
                status_code=429,
                detail="Too many attempts. Request a new recovery code.",
            )

        otp.attempts += 1

        if not secrets.compare_digest(self._hash(code), otp.code_hash):
            self.repository.save()
            raise HTTPException(
                status_code=400,
                detail="Invalid or expired recovery code.",
            )

        # Replace the OTP hash with a one-time reset-token hash.
        reset_token = secrets.token_urlsafe(32)

        otp.consumed_at = now
        otp.code_hash = self._hash(reset_token)
        otp.expires_at = now + timedelta(
            minutes=RESET_TOKEN_EXPIRY_MINUTES
        )

        self.repository.save()

        return reset_token, otp.expires_at

    def reset_password(
        self,
        reset_token: str,
        new_password: str,
    ) -> None:
        grant = self.repository.get_password_reset_grant(
            self._hash(reset_token)
        )

        now = self._now()

        if grant is None:
            raise HTTPException(
                status_code=400,
                detail="Invalid or expired password reset token.",
            )

        expires_at = grant.expires_at

        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if expires_at <= now:
            raise HTTPException(
                status_code=400,
                detail="Invalid or expired password reset token.",
            )

        customer = (
            self.repository.get_customer_by_id(grant.customer_id)
            if grant.customer_id
            else None
        )

        if customer is None or not customer.is_active:
            raise HTTPException(
                status_code=400,
                detail="Invalid or expired password reset token.",
            )

        customer.password_hash = hash_password(new_password)

        # Invalidate the token so it cannot be reused.
        grant.code_hash = self._hash(secrets.token_urlsafe(32))
        grant.expires_at = now

        # Revoke existing sessions after a successful password reset.
        self.repository.revoke_customer_sessions(customer.id)

        self.repository.save()