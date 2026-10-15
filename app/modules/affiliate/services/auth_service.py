import logging
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.email import EmailService
from app.modules.affiliate.models.affiliate import Affiliate
from app.modules.affiliate.models.affiliate_session import AffiliateSession
from app.modules.affiliate.repositories.auth_repo import (
    AffiliateAuthRepository,
)
from app.modules.affiliate.security.security import (
    generate_token,
    hash_password,
    hash_token,
    needs_rehash,
    verify_password,
)

logger = logging.getLogger(__name__)

SESSION_DAYS = 7
ACTIVATION_HOURS = 24


class AffiliateAuthService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = AffiliateAuthRepository(db)

    def issue_activation_token(self, affiliate: Affiliate) -> str:
        if affiliate.status != "active":
            raise HTTPException(
                status_code=403,
                detail="Affiliate account is not active.",
            )

        raw_token = generate_token()

        affiliate.activation_token_hash = hash_token(raw_token)
        affiliate.activation_expires_at = (
            datetime.now(timezone.utc)
            + timedelta(hours=ACTIVATION_HOURS)
        )

        self.db.flush()
        return raw_token

    def send_activation_email(
        self,
        affiliate: Affiliate,
        raw_token: str,
    ) -> None:
        frontend_url = settings.frontend_base_url.rstrip("/")
        activation_url = (
            f"{frontend_url}/affiliate/activate?token={raw_token}"
        )

        safe_name = self._escape_html(affiliate.full_name)
        safe_url = self._escape_html(activation_url)

        html = f"""
        <div style="font-family:Arial,sans-serif;line-height:1.6;color:#222">
          <h2>Activate your EnergyMax affiliate account</h2>
          <p>Hello {safe_name},</p>
          <p>Your EnergyMax affiliate application has been approved.</p>
          <p>
            Use the button below to set your password and activate
            your account. This link expires in 24 hours.
          </p>
          <p>
            <a href="{safe_url}"
               style="display:inline-block;padding:12px 20px;
               background:#111;color:#fff;text-decoration:none;
               border-radius:6px">
               Activate account
            </a>
          </p>
          <p>If you did not expect this email, you can ignore it.</p>
        </div>
        """

        try:
            EmailService().send_email(
                to=affiliate.email,
                subject="Activate your EnergyMax affiliate account",
                html=html,
            )
        except Exception:
            logger.exception(
                "Failed to send affiliate activation email"
            )
            raise HTTPException(
                status_code=502,
                detail=(
                    "Affiliate account was saved, but the activation "
                    "email could not be sent. Ask an admin to resend it."
                ),
            )

    def activate(
        self,
        raw_token: str,
        new_password: str,
    ) -> None:
        if not raw_token or len(raw_token) > 256:
            raise HTTPException(
                status_code=400,
                detail="Invalid or expired activation link.",
            )

        affiliate = self.repo.get_by_activation_hash(
            hash_token(raw_token)
        )

        if affiliate is None or not affiliate.activation_expires_at:
            raise HTTPException(
                status_code=400,
                detail="Invalid or expired activation link.",
            )

        now = datetime.now(timezone.utc)
        expires_at = affiliate.activation_expires_at

        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if expires_at <= now or affiliate.password_hash:
            raise HTTPException(
                status_code=400,
                detail="Invalid or expired activation link.",
            )

        if affiliate.status != "active":
            raise HTTPException(
                status_code=403,
                detail="Affiliate account is not active.",
            )

        affiliate.password_hash = hash_password(new_password)
        affiliate.activated_at = now

        # Make the activation token single-use.
        affiliate.activation_token_hash = None
        affiliate.activation_expires_at = None

        self.db.flush()

    def login(
        self,
        email: str,
        password: str,
    ) -> tuple[Affiliate, str, datetime]:
        normalized_email = str(email).strip().lower()
        affiliate = self.repo.get_by_email(normalized_email)

        # Same response for unknown email and wrong password.
        if affiliate is None or not affiliate.password_hash:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
            )

        if not verify_password(password, affiliate.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
            )

        if affiliate.status != "active":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Affiliate account is not active.",
            )

        if needs_rehash(affiliate.password_hash):
            affiliate.password_hash = hash_password(password)

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=SESSION_DAYS)
        raw_token = generate_token()

        session = AffiliateSession(
            public_id=str(uuid4()),
            affiliate_id=affiliate.id,
            token_hash=hash_token(raw_token),
            expires_at=expires_at,
            is_active=True,
        )

        self.repo.create_session(session)
        affiliate.last_login_at = now

        self.db.flush()

        # Return the raw token only to the caller.
        # The database stores only its hash.
        return affiliate, raw_token, expires_at

    def authenticate_session(self, raw_token: str) -> Affiliate:
        if not raw_token or len(raw_token) > 256:
            raise HTTPException(
                status_code=401,
                detail="Affiliate authentication required.",
            )

        session = self.repo.get_session_by_hash(
            hash_token(raw_token)
        )

        if session is None or not session.is_active:
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired affiliate session.",
            )

        now = datetime.now(timezone.utc)
        expires_at = session.expires_at

        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if expires_at <= now:
            session.is_active = False
            session.revoked_at = now
            self.db.flush()

            raise HTTPException(
                status_code=401,
                detail="Invalid or expired affiliate session.",
            )

        affiliate = session.affiliate

        if (
            affiliate is None
            or affiliate.status != "active"
            or not affiliate.password_hash
        ):
            session.is_active = False
            session.revoked_at = now
            self.db.flush()

            raise HTTPException(
                status_code=403,
                detail="Affiliate account is not active.",
            )

        session.last_used_at = now
        return affiliate

    def logout(self, raw_token: str) -> None:
        token_hash = hash_token(raw_token)

        if not self.repo.revoke_session(token_hash):
            raise HTTPException(
                status_code=401,
                detail="Invalid affiliate session.",
            )

    @staticmethod
    def _escape_html(value: str) -> str:
        return (
            value.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#x27;")
        )