from datetime import datetime, timezone
from decimal import Decimal
import re

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.admin.auth.models.admin_user import AdminUser
from app.modules.affiliate.models.affiliate import Affiliate
from app.modules.affiliate.models.affiliate_withdrawal import (
    AffiliateWithdrawal,
)
from app.modules.affiliate.providers.base import (
    PayoutProviderStatus,
    PayoutResult,
)
from app.modules.affiliate.services.wallet_service import WalletService


ALLOWED_WITHDRAWAL_STATUSES = {
    "PENDING",
    "APPROVED",
    "PROCESSING",
    "PAID",
    "FAILED",
    "REJECTED",
}

MAX_PAGE_SIZE = 100
MAX_IDEMPOTENCY_KEY_LENGTH = 150
MAX_PROVIDER_REFERENCE_LENGTH = 150
MAX_BENEFICIARY_REFERENCE_LENGTH = 150
MAX_PROVIDER_NAME_LENGTH = 30
MAX_REASON_LENGTH = 2000

CURRENCY_PATTERN = re.compile(r"^[A-Z]{3}$")


class WithdrawalService:
    def __init__(self, db: Session):
        self.db = db

    # ---------------------------------------------------------
    # VALIDATION HELPERS
    # ---------------------------------------------------------

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _validate_pagination(
        limit: int,
        offset: int,
    ) -> None:
        if not 1 <= limit <= MAX_PAGE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Limit must be between 1 and {MAX_PAGE_SIZE}.",
            )

        if offset < 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Offset cannot be negative.",
            )

    @staticmethod
    def _normalize_currency(currency: str) -> str:
        if not isinstance(currency, str):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="A valid currency is required.",
            )

        normalized = currency.strip().upper()

        if not CURRENCY_PATTERN.fullmatch(normalized):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Currency must be a valid three-letter code.",
            )

        return normalized

    @staticmethod
    def _validate_idempotency_key(key: str) -> str:
        if not isinstance(key, str):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="An idempotency key is required.",
            )

        key = key.strip()

        if not key:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="An idempotency key cannot be empty.",
            )

        if len(key) > MAX_IDEMPOTENCY_KEY_LENGTH:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "Idempotency key cannot exceed "
                    f"{MAX_IDEMPOTENCY_KEY_LENGTH} characters."
                ),
            )

        return key

    @staticmethod
    def _validate_reason(reason: str) -> str:
        if not isinstance(reason, str):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="A rejection reason is required.",
            )

        reason = reason.strip()

        if not reason:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="A rejection reason cannot be empty.",
            )

        if len(reason) > MAX_REASON_LENGTH:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Reason cannot exceed {MAX_REASON_LENGTH} characters."
                ),
            )

        return reason

    @staticmethod
    def _validate_reference(
        value: str,
        *,
        field_name: str,
        max_length: int,
    ) -> str:
        if not isinstance(value, str):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"{field_name} is required.",
            )

        value = value.strip()

        if not value:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"{field_name} cannot be empty.",
            )

        if len(value) > max_length:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"{field_name} cannot exceed {max_length} characters."
                ),
            )

        return value

    # ---------------------------------------------------------
    # CREATE WITHDRAWAL
    # ---------------------------------------------------------

    def create_request(
        self,
        affiliate: Affiliate,
        *,
        amount: Decimal,
        currency: str,
        idempotency_key: str,
    ) -> AffiliateWithdrawal:

        try:
            amount = WalletService.money(amount)
        except (ValueError, TypeError, ArithmeticError):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid withdrawal amount.",
            )

        currency = self._normalize_currency(currency)
        idempotency_key = self._validate_idempotency_key(
            idempotency_key
        )

        if not amount.is_finite() or amount <= Decimal("0.00"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Withdrawal amount must be a positive finite value.",
            )

        # First check: return an identical previous request.
        existing = self.db.scalar(
            select(AffiliateWithdrawal).where(
                AffiliateWithdrawal.idempotency_key == idempotency_key
            )
        )

        if existing is not None:
            return self._return_if_same_request(
                existing,
                affiliate_id=affiliate.id,
                amount=amount,
                currency=currency,
            )

        # Serialize wallet-sensitive withdrawal requests for this affiliate.
        # The transaction must remain open until the caller commits or rolls
        # back. This is effective with a database that supports row locking.
        locked_affiliate_id = self.db.scalar(
            select(Affiliate.id)
            .where(Affiliate.id == affiliate.id)
            .with_for_update()
        )

        if locked_affiliate_id is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Affiliate account not found.",
            )

        # Recheck after acquiring the affiliate lock.
        existing = self.db.scalar(
            select(AffiliateWithdrawal).where(
                AffiliateWithdrawal.idempotency_key == idempotency_key
            )
        )

        if existing is not None:
            return self._return_if_same_request(
                existing,
                affiliate_id=affiliate.id,
                amount=amount,
                currency=currency,
            )

        available = WalletService(self.db).get_available_balance(
            affiliate,
            currency,
        )

        if amount > available:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Insufficient available balance.",
            )

        withdrawal = AffiliateWithdrawal(
            affiliate_id=affiliate.id,
            amount=amount,
            currency=currency,
            status="PENDING",
            idempotency_key=idempotency_key,
        )

        self.db.add(withdrawal)
        self.db.flush()

        return withdrawal

    @staticmethod
    def _return_if_same_request(
        existing: AffiliateWithdrawal,
        *,
        affiliate_id: int,
        amount: Decimal,
        currency: str,
    ) -> AffiliateWithdrawal:

        if (
            existing.affiliate_id == affiliate_id
            and existing.amount == amount
            and existing.currency == currency
        ):
            return existing

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Idempotency key was used for a different request.",
        )

    # ---------------------------------------------------------
    # AFFILIATE WITHDRAWAL HISTORY
    # ---------------------------------------------------------

    def list_for_affiliate(
        self,
        affiliate: Affiliate,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AffiliateWithdrawal]:

        self._validate_pagination(limit, offset)

        query = (
            select(AffiliateWithdrawal)
            .where(
                AffiliateWithdrawal.affiliate_id == affiliate.id
            )
            .order_by(
                AffiliateWithdrawal.requested_at.desc(),
                AffiliateWithdrawal.id.desc(),
            )
            .limit(limit)
            .offset(offset)
        )

        return list(self.db.scalars(query).all())

    # ---------------------------------------------------------
    # ADMIN WITHDRAWAL HISTORY
    # ---------------------------------------------------------

    def list_for_admin(
        self,
        *,
        withdrawal_status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AffiliateWithdrawal]:

        self._validate_pagination(limit, offset)

        query = select(AffiliateWithdrawal)

        if withdrawal_status is not None:
            normalized = withdrawal_status.strip().upper()

            if normalized not in ALLOWED_WITHDRAWAL_STATUSES:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Invalid withdrawal status.",
                )

            query = query.where(
                AffiliateWithdrawal.status == normalized
            )

        query = (
            query
            .order_by(
                AffiliateWithdrawal.requested_at.desc(),
                AffiliateWithdrawal.id.desc(),
            )
            .limit(limit)
            .offset(offset)
        )

        return list(self.db.scalars(query).all())

    # ---------------------------------------------------------
    # GET WITHDRAWAL
    # ---------------------------------------------------------

    def get_by_public_id(
        self,
        public_id: str,
    ) -> AffiliateWithdrawal:

        withdrawal = self.db.scalar(
            select(AffiliateWithdrawal).where(
                AffiliateWithdrawal.public_id == public_id
            )
        )

        if withdrawal is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Withdrawal request not found.",
            )

        return withdrawal

    # ---------------------------------------------------------
    # APPROVE WITHDRAWAL
    # ---------------------------------------------------------

    def approve(
        self,
        public_id: str,
        admin: AdminUser,
    ) -> AffiliateWithdrawal:

        withdrawal = self._lock_withdrawal(public_id)

        if withdrawal.status != "PENDING":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only pending requests can be approved.",
            )

        withdrawal.status = "APPROVED"
        withdrawal.reviewed_by_admin_id = admin.id
        withdrawal.reviewed_at = self._now()

        self.db.flush()

        return withdrawal

    # ---------------------------------------------------------
    # REJECT WITHDRAWAL
    # ---------------------------------------------------------

    def reject(
        self,
        public_id: str,
        admin: AdminUser,
        reason: str,
    ) -> AffiliateWithdrawal:

        reason = self._validate_reason(reason)
        withdrawal = self._lock_withdrawal(public_id)

        if withdrawal.status != "PENDING":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only pending requests can be rejected.",
            )

        withdrawal.status = "REJECTED"
        withdrawal.rejection_reason = reason
        withdrawal.reviewed_by_admin_id = admin.id
        withdrawal.reviewed_at = self._now()

        self.db.flush()

        return withdrawal

    # ---------------------------------------------------------
    # START PAYOUT PROCESSING
    # ---------------------------------------------------------

    def start_processing(
        self,
        public_id: str,
        admin: AdminUser,
        *,
        provider: str,
        beneficiary_reference: str,
    ) -> AffiliateWithdrawal:
        """
        Transition an approved withdrawal into PROCESSING.

        This method does not itself call the payout provider.
        The external payout integration must be implemented separately.
        """

        provider = self._validate_reference(
            provider,
            field_name="Provider",
            max_length=MAX_PROVIDER_NAME_LENGTH,
        ).upper()

        beneficiary_reference = self._validate_reference(
            beneficiary_reference,
            field_name="Beneficiary reference",
            max_length=MAX_BENEFICIARY_REFERENCE_LENGTH,
        )

        withdrawal = self._lock_withdrawal(public_id)

        if withdrawal.status != "APPROVED":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only approved requests can enter processing.",
            )

        withdrawal.status = "PROCESSING"
        withdrawal.provider = provider
        withdrawal.beneficiary_reference = beneficiary_reference
        withdrawal.payment_initiated_at = self._now()
        withdrawal.failure_reason = None
        withdrawal.last_provider_status = (
            PayoutProviderStatus.UNKNOWN.value
        )

        self.db.flush()

        return withdrawal

    # ---------------------------------------------------------
    # RECORD PROVIDER RESULT
    # ---------------------------------------------------------

    def record_provider_result(
        self,
        public_id: str,
        result: PayoutResult,
    ) -> AffiliateWithdrawal:
        """
        Record a result from a trusted provider adapter or verified webhook.

        SUCCESS -> PAID
        FAILED  -> FAILED
        Other statuses remain PROCESSING.

        This method must not be exposed through an unauthenticated endpoint.
        """

        if not isinstance(result.status, PayoutProviderStatus):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid payout provider status.",
            )

        provider = self._validate_reference(
            result.provider,
            field_name="Provider",
            max_length=MAX_PROVIDER_NAME_LENGTH,
        ).upper()

        provider_reference = result.provider_reference

        if provider_reference is not None:
            provider_reference = self._validate_reference(
                provider_reference,
                field_name="Provider reference",
                max_length=MAX_PROVIDER_REFERENCE_LENGTH,
            )

        withdrawal = self._lock_withdrawal(public_id)

        # Provider identity must match before accepting any result.
        if (
            not withdrawal.provider
            or withdrawal.provider.upper() != provider
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Payout provider does not match the withdrawal.",
            )

        # Allow a duplicate terminal callback only when it matches the
        # already-recorded terminal result.
        if withdrawal.status in {"PAID", "FAILED"}:
            same_terminal_status = (
                withdrawal.status == "PAID"
                and result.status == PayoutProviderStatus.SUCCESS
            ) or (
                withdrawal.status == "FAILED"
                and result.status == PayoutProviderStatus.FAILED
            )

            same_reference = (
                withdrawal.provider_reference == provider_reference
                and provider_reference is not None
            )

            if same_terminal_status and same_reference:
                return withdrawal

            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Withdrawal already has a terminal result that "
                    "conflicts with this provider response."
                ),
            )

        if withdrawal.status != "PROCESSING":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Provider results can only be recorded for "
                    "processing withdrawals."
                ),
            )

        # A provider reference must not silently change after one has
        # already been stored for this withdrawal.
        if (
            withdrawal.provider_reference is not None
            and provider_reference is not None
            and withdrawal.provider_reference != provider_reference
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Provider reference does not match the existing reference.",
            )

        if provider_reference is not None:
            withdrawal.provider_reference = provider_reference
            withdrawal.payout_reference = provider_reference

        withdrawal.last_provider_status = result.status.value

        if result.status == PayoutProviderStatus.SUCCESS:
            if not provider_reference:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        "A provider reference is required for "
                        "successful payouts."
                    ),
                )

            withdrawal.status = "PAID"
            withdrawal.paid_at = self._now()
            withdrawal.failure_reason = None

        elif result.status == PayoutProviderStatus.FAILED:
            message = (result.message or "Payout failed.").strip()
            withdrawal.status = "FAILED"
            withdrawal.failure_reason = message[:MAX_REASON_LENGTH]
            withdrawal.paid_at = None

        else:
            # ACCEPTED, PROCESSING and UNKNOWN do not prove that the
            # transfer succeeded.
            withdrawal.status = "PROCESSING"

        self.db.flush()

        return withdrawal

    # ---------------------------------------------------------
    # INTERNAL ROW LOCK
    # ---------------------------------------------------------

    def _lock_withdrawal(
        self,
        public_id: str,
    ) -> AffiliateWithdrawal:

        withdrawal = self.db.scalar(
            select(AffiliateWithdrawal)
            .where(AffiliateWithdrawal.public_id == public_id)
            .with_for_update()
        )

        if withdrawal is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Withdrawal request not found.",
            )

        return withdrawal