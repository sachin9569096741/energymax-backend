from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.affiliate.models.affiliate_commission_ledger import (
    AffiliateCommissionLedger,
)


CENT = Decimal("0.01")


class CommissionLedgerMutationService:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def money(value: Decimal) -> Decimal:
        return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)

    def _find_idempotent_entry(
        self,
        idempotency_key: str,
    ) -> AffiliateCommissionLedger | None:
        return self.db.scalar(
            select(AffiliateCommissionLedger).where(
                AffiliateCommissionLedger.idempotency_key
                == idempotency_key
            )
        )

    def _ensure_idempotency_available(
        self,
        idempotency_key: str,
        *,
        entry_type: str,
        affiliate_id: int,
        order_id: int,
        amount: Decimal,
        currency: str,
        reverses_entry_id: int | None,
        description: str,
    ) -> AffiliateCommissionLedger | None:
        existing = self._find_idempotent_entry(idempotency_key)

        if existing is None:
            return None

        matches = (
            existing.entry_type == entry_type
            and existing.affiliate_id == affiliate_id
            and existing.order_id == order_id
            and self.money(Decimal(existing.amount)) == amount
            and existing.currency == currency
            and existing.reverses_entry_id == reverses_entry_id
            and existing.description == description
        )

        if not matches:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Idempotency key was already used for a different "
                    "ledger operation."
                ),
            )

        return existing

    def adjust(
        self,
        *,
        original: AffiliateCommissionLedger,
        amount: Decimal,
        currency: str,
        description: str,
        idempotency_key: str,
        admin_id: int,
    ) -> AffiliateCommissionLedger:
        amount = self.money(amount)
        currency = currency.strip().upper()

        if amount == 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Adjustment amount cannot be zero.",
            )

        if currency != original.currency:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Adjustment currency must match the original entry.",
            )

        if original.entry_type != "COMMISSION":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Only an original commission can be adjusted.",
            )

        existing = self._ensure_idempotency_available(
            idempotency_key,
            entry_type="ADJUSTMENT",
            affiliate_id=original.affiliate_id,
            order_id=original.order_id,
            amount=amount,
            currency=currency,
            reverses_entry_id=None,
            description=description,
        )

        if existing is not None:
            return existing

        entry = AffiliateCommissionLedger(
            affiliate_id=original.affiliate_id,
            attribution_id=original.attribution_id,
            order_id=original.order_id,
            entry_type="ADJUSTMENT",
            amount=amount,
            currency=currency,
            base_amount=Decimal("0.00"),
            commission_rate=original.commission_rate,
            idempotency_key=idempotency_key,
            reverses_entry_id=None,
            description=(
                f"{description} [admin_id={admin_id}; "
                f"original_entry_id={original.id}]"
            ),
        )

        # Preserve the admin and original-entry references in the audit text.
        # Flush now so DB constraints are checked before the route commits.
        self.db.add(entry)
        self.db.flush()
        return entry

    def reverse(
        self,
        *,
        original: AffiliateCommissionLedger,
        reason: str,
        idempotency_key: str,
        admin_id: int,
    ) -> AffiliateCommissionLedger:
        if original.entry_type != "COMMISSION":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Only an original commission can be reversed.",
            )

        reversal_amount = -abs(self.money(Decimal(original.amount)))
        description = (
            f"Reversal: {reason} [admin_id={admin_id}; "
            f"original_entry_id={original.id}]"
        )

        existing = self._ensure_idempotency_available(
            idempotency_key,
            entry_type="REVERSAL",
            affiliate_id=original.affiliate_id,
            order_id=original.order_id,
            amount=reversal_amount,
            currency=original.currency,
            reverses_entry_id=original.id,
            description=description,
        )

        if existing is not None:
            return existing

        prior_reversal = self.db.scalar(
            select(AffiliateCommissionLedger).where(
                AffiliateCommissionLedger.reverses_entry_id == original.id,
                AffiliateCommissionLedger.entry_type == "REVERSAL",
            )
        )

        if prior_reversal is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This commission has already been reversed.",
            )

        entry = AffiliateCommissionLedger(
            affiliate_id=original.affiliate_id,
            attribution_id=original.attribution_id,
            order_id=original.order_id,
            entry_type="REVERSAL",
            amount=reversal_amount,
            currency=original.currency,
            base_amount=-abs(self.money(Decimal(original.base_amount))),
            commission_rate=original.commission_rate,
            idempotency_key=idempotency_key,
            reverses_entry_id=original.id,
            description=description,
        )

        self.db.add(entry)
        self.db.flush()
        return entry