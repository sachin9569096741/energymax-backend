from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.admin.auth.models.admin_user import AdminUser
from app.modules.affiliate.models.affiliate import Affiliate
from app.modules.affiliate.models.affiliate_withdrawal import (
    AffiliateWithdrawal,
)
from app.modules.affiliate.services.wallet_service import WalletService


class WithdrawalService:
    def __init__(self, db: Session):
        self.db = db

    def create_request(
        self,
        affiliate: Affiliate,
        *,
        amount: Decimal,
        currency: str,
        idempotency_key: str,
    ) -> AffiliateWithdrawal:
        amount = WalletService.money(amount)
        currency = currency.strip().upper()

        if amount <= 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Withdrawal amount must be positive.",
            )

        existing = self.db.scalar(
            select(AffiliateWithdrawal).where(
                AffiliateWithdrawal.idempotency_key == idempotency_key
            )
        )

        if existing is not None:
            if (
                existing.affiliate_id == affiliate.id
                and existing.amount == amount
                and existing.currency == currency
            ):
                return existing

            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Idempotency key was used for a different request.",
            )

        # Serialize balance-sensitive operations for this affiliate.
        # This lock is effective only when the surrounding transaction
        # commits or rolls back normally.
        self.db.execute(
            select(Affiliate.id)
            .where(Affiliate.id == affiliate.id)
            .with_for_update()
        ).scalar_one()

        # Recheck after obtaining the lock, because another request may
        # have been created while this transaction waited.
        existing = self.db.scalar(
            select(AffiliateWithdrawal).where(
                AffiliateWithdrawal.idempotency_key == idempotency_key
            )
        )

        if existing is not None:
            if (
                existing.affiliate_id == affiliate.id
                and existing.amount == amount
                and existing.currency == currency
            ):
                return existing

            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Idempotency key was used for a different request.",
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

    def list_for_affiliate(
        self,
        affiliate: Affiliate,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AffiliateWithdrawal]:
        query = (
            select(AffiliateWithdrawal)
            .where(AffiliateWithdrawal.affiliate_id == affiliate.id)
            .order_by(
                AffiliateWithdrawal.requested_at.desc(),
                AffiliateWithdrawal.id.desc(),
            )
            .limit(limit)
            .offset(offset)
        )

        return list(self.db.scalars(query).all())

    def list_for_admin(
        self,
        *,
        withdrawal_status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AffiliateWithdrawal]:
        query = select(AffiliateWithdrawal)

        if withdrawal_status:
            normalized = withdrawal_status.strip().upper()
            allowed = {"PENDING", "APPROVED", "REJECTED", "PAID"}

            if normalized not in allowed:
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
        withdrawal.reviewed_at = datetime.now(timezone.utc)

        self.db.flush()
        return withdrawal

    def reject(
        self,
        public_id: str,
        admin: AdminUser,
        reason: str,
    ) -> AffiliateWithdrawal:
        withdrawal = self._lock_withdrawal(public_id)

        if withdrawal.status != "PENDING":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only pending requests can be rejected.",
            )

        withdrawal.status = "REJECTED"
        withdrawal.rejection_reason = reason.strip()
        withdrawal.reviewed_by_admin_id = admin.id
        withdrawal.reviewed_at = datetime.now(timezone.utc)

        self.db.flush()
        return withdrawal

    def mark_paid(
        self,
        public_id: str,
        admin: AdminUser,
        payout_reference: str,
    ) -> AffiliateWithdrawal:
        withdrawal = self._lock_withdrawal(public_id)

        if withdrawal.status != "APPROVED":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only approved requests can be marked paid.",
            )

        withdrawal.status = "PAID"
        withdrawal.payout_reference = payout_reference.strip()
        withdrawal.reviewed_by_admin_id = admin.id
        withdrawal.reviewed_at = (
            withdrawal.reviewed_at or datetime.now(timezone.utc)
        )
        withdrawal.paid_at = datetime.now(timezone.utc)

        self.db.flush()
        return withdrawal

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