
import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import HTTPException, status

from app.core.email import EmailService
from app.modules.shop.customer.models.customer_otp import CustomerOTP
from app.modules.shop.customer.models.customer_session import CustomerSession
from app.modules.shop.customer.repositories.customer_auth import (
    CustomerAuthRepository,
)
from app.modules.shop.customer.services.email_templates import (
    build_customer_otp_email,
)
from app.modules.shop.customer.security.security import (
    generate_session_token,
    hash_session_token,
)


logger = logging.getLogger(__name__)

OTP_LENGTH = 6
OTP_EXPIRY_MINUTES = 10
OTP_MAX_ATTEMPTS = 5
CUSTOMER_SESSION_DAYS = 30


class CustomerOTPService:
    def __init__(self, repository: CustomerAuthRepository):
        self.repository = repository
        self.email_service = EmailService()

    def request_otp(
        self,
        destination: str,
        channel: str,
        purpose: str,
    ):
        channel = channel.strip().lower()
        purpose = purpose.strip().lower()
        destination = self._normalize_destination(destination, channel)

        self._validate_channel(channel)
        self._validate_purpose(purpose)

        if channel != "email":
            raise HTTPException(
                status_code=400,
                detail="SMS OTP is not available yet.",
            )

        if purpose == "password_reset":
            raise HTTPException(
                status_code=400,
                detail="Password reset is not implemented yet.",
            )

        customer = self._find_customer(destination, channel)

        if customer is None:
            raise HTTPException(
                status_code=404,
                detail="Customer account not found.",
            )

        if not customer.is_active:
            raise HTTPException(
                status_code=403,
                detail="Customer account is inactive.",
            )

        if purpose == "registration" and customer.email_verified:
            raise HTTPException(
                status_code=409,
                detail="This email address is already verified.",
            )

        if purpose == "login" and not customer.email_verified:
            raise HTTPException(
                status_code=403,
                detail="Please verify your email before logging in.",
            )

        now = datetime.now(timezone.utc)

        self.repository.invalidate_active_otps(
            destination=destination,
            channel=channel,
            purpose=purpose,
        )

        otp_code = f"{secrets.randbelow(1_000_000):06d}"
        expires_at = now + timedelta(minutes=OTP_EXPIRY_MINUTES)

        otp = CustomerOTP(
            public_id=str(uuid4()),
            customer_id=customer.id,
            destination=destination,
            channel=channel,
            purpose=purpose,
            code_hash=self._hash_otp(otp_code),
            expires_at=expires_at,
            attempts=0,
            max_attempts=OTP_MAX_ATTEMPTS,
        )

        self.repository.create_otp(otp)

        html = build_customer_otp_email(
            otp_code=otp_code,
            purpose=purpose,
        )

        try:
            self.email_service.send_email(
                to=destination,
                subject="Verify your EnergyMaxGroup email",
                html=html,
            )
        except Exception:
            logger.exception(
                "Failed to send customer OTP email for purpose=%s",
                purpose,
            )
            raise HTTPException(
                status_code=502,
                detail="Unable to send verification email. Please try again.",
            )

        logger.info(
            "Customer OTP email requested for purpose=%s",
            purpose,
        )

        return expires_at, otp_code

    def verify_otp(
        self,
        destination: str,
        channel: str,
        purpose: str,
        code: str,
    ):
        channel = channel.strip().lower()
        purpose = purpose.strip().lower()
        destination = self._normalize_destination(destination, channel)

        self._validate_channel(channel)
        self._validate_purpose(purpose)

        if channel != "email":
            raise HTTPException(
                status_code=400,
                detail="SMS OTP is not available yet.",
            )

        if purpose == "password_reset":
            raise HTTPException(
                status_code=400,
                detail="Password reset verification is not implemented yet.",
            )

        otp = self.repository.get_latest_otp(
            destination=destination,
            channel=channel,
            purpose=purpose,
        )

        if otp is None:
            raise HTTPException(status_code=400, detail="Invalid OTP.")

        if otp.consumed_at is not None:
            raise HTTPException(
                status_code=400,
                detail="OTP has already been used.",
            )

        now = datetime.now(timezone.utc)

        if otp.expires_at <= now:
            raise HTTPException(
                status_code=400,
                detail="OTP has expired.",
            )

        if otp.attempts >= otp.max_attempts:
            raise HTTPException(
                status_code=429,
                detail="Maximum OTP attempts exceeded.",
            )

        otp.attempts += 1

        if not secrets.compare_digest(
            self._hash_otp(code),
            otp.code_hash,
        ):
            self.repository.save()
            raise HTTPException(
                status_code=400,
                detail="Invalid OTP.",
            )

        customer = (
            self.repository.get_customer_by_id(otp.customer_id)
            if otp.customer_id is not None
            else None
        )

        if customer is None:
            raise HTTPException(
                status_code=404,
                detail="Customer account associated with this OTP was not found.",
            )

        if not customer.is_active:
            raise HTTPException(
                status_code=403,
                detail="Customer account is inactive.",
            )

        if not customer.email or customer.email.lower() != destination:
            raise HTTPException(
                status_code=400,
                detail="OTP does not match the customer's email address.",
            )

        if purpose == "registration" and customer.email_verified:
            raise HTTPException(
                status_code=409,
                detail="This email address is already verified.",
            )

        if purpose == "login" and not customer.email_verified:
            raise HTTPException(
                status_code=403,
                detail="Please verify your email before logging in.",
            )

        otp.consumed_at = now

        if purpose == "registration":
            customer.email_verified = True

        customer.last_login_at = now

        session_token = secrets.token_urlsafe(32)
        token_hash = hash_session_token(session_token)

        session = CustomerSession(
            public_id=str(uuid4()),
            customer_id=customer.id,
            token_hash=token_hash,
            expires_at=now + timedelta(days=CUSTOMER_SESSION_DAYS),
            is_active=True,
        )

        self.repository.create_session(session)
        self.repository.save()

        return customer, session_token

    def _find_customer(self, destination: str, channel: str):
        if channel == "email":
            return self.repository.get_customer_by_email(destination)

        return self.repository.get_customer_by_phone(destination)

    @staticmethod
    def _hash_otp(code: str) -> str:
        return hashlib.sha256(code.encode("utf-8")).hexdigest()

    @staticmethod
    def _normalize_destination(destination: str, channel: str) -> str:
        destination = destination.strip()

        if channel == "email":
            return destination.lower()

        return destination.replace(" ", "").replace("-", "")

    @staticmethod
    def _validate_channel(channel: str) -> None:
        if channel not in {"email", "sms"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Channel must be either 'email' or 'sms'.",
            )

    @staticmethod
    def _validate_purpose(purpose: str) -> None:
        if purpose not in {"login", "registration", "password_reset"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Purpose must be 'login', "
                    "'registration', or 'password_reset'."
                ),
            )
