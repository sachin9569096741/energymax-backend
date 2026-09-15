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


class CustomerOTPService:
    def __init__(self, repository: CustomerAuthRepository):
        self.repository = repository
        self.email_service = EmailService()

    def request_otp(
        self,
        destination: str,
        channel: str,
        purpose: str,
    ) -> tuple[datetime, str]:

        channel = channel.strip().lower()
        purpose = purpose.strip().lower()
        destination = self._normalize_destination(
            destination,
            channel,
        )

        self._validate_channel(channel)
        self._validate_purpose(purpose)

        # We are implementing email OTP first.
        if channel != "email":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="SMS OTP is not available yet.",
            )

        customer = self._find_customer(
            destination,
            channel,
        )

        if purpose == "login" and customer is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No customer account found for this destination.",
            )

        if purpose == "registration" and customer is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A customer account already exists for this destination.",
            )

        # Invalidate previous active OTPs for the same
        # destination/channel/purpose.
        self.repository.invalidate_active_otps(
            destination=destination,
            channel=channel,
            purpose=purpose,
        )

        otp_code = self._generate_otp()
        code_hash = self._hash_otp(otp_code)

        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=OTP_EXPIRY_MINUTES
        )

        otp = CustomerOTP(
            public_id=str(uuid4()),
            customer_id=customer.id if customer else None,
            channel=channel,
            destination=destination,
            purpose=purpose,
            code_hash=code_hash,
            expires_at=expires_at,
            attempts=0,
            max_attempts=OTP_MAX_ATTEMPTS,
        )

        self.repository.create_otp(otp)

        # Send OTP through Resend.
        html = build_customer_otp_email(otp_code)

        self.email_service.send_email(
            to=destination,
            subject="Your EnergyMax OTP",
            html=html,
        )

        # Do NOT log the actual OTP.
        logger.info(
            "Customer OTP sent: channel=%s destination=%s "
            "purpose=%s expires_at=%s",
            channel,
            destination,
            purpose,
            expires_at,
        )

        return expires_at, otp_code

    def _find_customer(
        self,
        destination: str,
        channel: str,
    ):
        if channel == "email":
            return self.repository.get_customer_by_email(destination)

        return self.repository.get_customer_by_phone(destination)

    @staticmethod
    def _generate_otp() -> str:
        return f"{secrets.randbelow(1_000_000):06d}"

    @staticmethod
    def _hash_otp(code: str) -> str:
        return hashlib.sha256(
            code.encode("utf-8")
        ).hexdigest()

    @staticmethod
    def _normalize_destination(
        destination: str,
        channel: str,
    ) -> str:
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
        if purpose not in {
            "login",
            "registration",
            "password_reset",
        }:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Purpose must be 'login', "
                    "'registration', or 'password_reset'."
                ),
            )

    def verify_otp(self, destination, channel, purpose, code):
        channel = channel.strip().lower()
        purpose = purpose.strip().lower()
        destination = self._normalize_destination(destination, channel)

        self._validate_channel(channel)
        self._validate_purpose(purpose)

        if channel != "email":
            raise HTTPException(400, "SMS OTP is not available yet.")

        otp = self.repository.get_latest_otp(
            destination=destination,
            channel=channel,
            purpose=purpose,
        )

        if otp is None:
            raise HTTPException(400, "Invalid OTP.")

        if otp.consumed_at is not None:
            raise HTTPException(400, "OTP has already been used.")

        now = datetime.now(timezone.utc)

        if otp.expires_at <= now:
            raise HTTPException(400, "OTP has expired.")

        if otp.attempts >= otp.max_attempts:
            raise HTTPException(429, "Maximum OTP attempts exceeded.")

        otp.attempts += 1

        if not secrets.compare_digest(
            self._hash_otp(code),
            otp.code_hash,
        ):
            self.repository.save()
            raise HTTPException(400, "Invalid OTP.")

        # OTP is valid
        otp.consumed_at = now

        customer = None

        if otp.customer_id is not None:
            customer = self.repository.get_customer_by_id(otp.customer_id)

        # Login OTP must belong to an existing customer
        if purpose == "login" and customer is None:
            raise HTTPException(
                status_code=404,
                detail="Customer account not found.",
            )

        if customer is not None:
            if not customer.is_active:
                raise HTTPException(
                    status_code=403,
                    detail="Customer account is inactive.",
                )

            customer.last_login_at = now
            # Email OTP successfully verified, create a session token for the customer.
            customer.email_verified = True
            customer.last_login_at = now
            
            # Create customer session
            session_token = generate_session_token()
            token_hash = hash_session_token(session_token)

            expires_at = now + timedelta(days=30)

            session = CustomerSession(
                public_id=str(uuid4()),
                customer_id=customer.id,
                token_hash=token_hash,
                expires_at=expires_at,
                is_active=True,
            )

            self.repository.create_session(session)

            self.repository.save()

            return customer, session_token

        self.repository.save()

        return None, None