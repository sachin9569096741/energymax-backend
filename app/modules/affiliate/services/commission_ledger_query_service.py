from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.affiliate.models.affiliate import Affiliate
from app.modules.affiliate.models.affiliate_commission_ledger import (
    AffiliateCommissionLedger,
)


class CommissionLedgerQueryService:
    def __init__(self, db: Session):
        self.db = db

    def list_commissions(
        self,
        *,
        affiliate_public_id: str | None = None,
        entry_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AffiliateCommissionLedger]:
        query = select(AffiliateCommissionLedger)

        if affiliate_public_id:
            affiliate = self.db.scalar(
                select(Affiliate).where(
                    Affiliate.public_id == affiliate_public_id
                )
            )

            if affiliate is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Affiliate not found.",
                )

            query = query.where(
                AffiliateCommissionLedger.affiliate_id == affiliate.id
            )

        if entry_type:
            normalized_type = entry_type.strip().upper()
            allowed_types = {"COMMISSION", "REVERSAL", "ADJUSTMENT"}

            if normalized_type not in allowed_types:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        "entry_type must be COMMISSION, "
                        "REVERSAL, or ADJUSTMENT."
                    ),
                )

            query = query.where(
                AffiliateCommissionLedger.entry_type == normalized_type
            )

        query = (
            query
            .order_by(
                AffiliateCommissionLedger.created_at.desc(),
                AffiliateCommissionLedger.id.desc(),
            )
            .limit(limit)
            .offset(offset)
        )

        return list(self.db.scalars(query).all())

    def get_commission(
        self,
        public_id: str,
    ) -> AffiliateCommissionLedger:
        commission = self.db.scalar(
            select(AffiliateCommissionLedger).where(
                AffiliateCommissionLedger.public_id == public_id
            )
        )

        if commission is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Commission ledger entry not found.",
            )

        return commission

    def list_affiliate_commissions(
        self,
        affiliate: Affiliate,
        *,
        entry_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AffiliateCommissionLedger]:
        query = select(AffiliateCommissionLedger).where(
            AffiliateCommissionLedger.affiliate_id == affiliate.id
        )

        if entry_type:
            normalized_type = entry_type.strip().upper()
            allowed_types = {"COMMISSION", "REVERSAL", "ADJUSTMENT"}

            if normalized_type not in allowed_types:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        "entry_type must be COMMISSION, "
                        "REVERSAL, or ADJUSTMENT."
                    ),
                )

            query = query.where(
                AffiliateCommissionLedger.entry_type == normalized_type
            )

        query = (
            query
            .order_by(
                AffiliateCommissionLedger.created_at.desc(),
                AffiliateCommissionLedger.id.desc(),
            )
            .limit(limit)
            .offset(offset)
        )

        return list(self.db.scalars(query).all())

    def get_earnings_summary(
        self,
        affiliate: Affiliate,
    ) -> dict:
        rows = self.db.execute(
            select(
                AffiliateCommissionLedger.currency,
                AffiliateCommissionLedger.entry_type,
                func.coalesce(
                    func.sum(AffiliateCommissionLedger.amount),
                    Decimal("0.00"),
                ).label("total"),
                func.count(AffiliateCommissionLedger.id).label("count"),
            )
            .where(
                AffiliateCommissionLedger.affiliate_id == affiliate.id
            )
            .group_by(
                AffiliateCommissionLedger.currency,
                AffiliateCommissionLedger.entry_type,
            )
        ).all()

        # Keep currencies separate; never combine different currencies.
        totals: dict[str, dict] = {}

        for row in rows:
            currency = row.currency

            if currency not in totals:
                totals[currency] = {
                    "COMMISSION": Decimal("0.00"),
                    "REVERSAL": Decimal("0.00"),
                    "ADJUSTMENT": Decimal("0.00"),
                    "commission_count": 0,
                }

            totals[currency][row.entry_type] += Decimal(str(row.total))

            if row.entry_type == "COMMISSION":
                totals[currency]["commission_count"] += int(row.count)

        result = []

        for currency, values in sorted(totals.items()):
            commissions = values["COMMISSION"]
            reversals = values["REVERSAL"]
            adjustments = values["ADJUSTMENT"]

            result.append(
                {
                    "currency": currency,
                    "total_commissions": commissions,
                    "total_reversals": reversals,
                    "total_adjustments": adjustments,
                    "net_earnings": (
                        commissions + reversals + adjustments
                    ),
                    "commission_count": values["commission_count"],
                }
            )

        return result