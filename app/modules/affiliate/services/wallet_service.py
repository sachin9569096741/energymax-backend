from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.affiliate.models.affiliate import Affiliate
from app.modules.affiliate.models.affiliate_commission_ledger import (
    AffiliateCommissionLedger,
)
from app.modules.affiliate.models.affiliate_withdrawal import (
    AffiliateWithdrawal,
)


CENT = Decimal("0.01")
ACTIVE_WITHDRAWAL_STATES = ("PENDING", "APPROVED", "PROCESSING",)


class WalletService:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def money(value) -> Decimal:
        return Decimal(str(value or "0")).quantize(
            CENT,
            rounding=ROUND_HALF_UP,
        )

    def get_wallet(self, affiliate: Affiliate) -> list[dict]:
        earnings_rows = self.db.execute(
            select(
                AffiliateCommissionLedger.currency,
                func.coalesce(
                    func.sum(AffiliateCommissionLedger.amount),
                    0,
                ),
            )
            .where(
                AffiliateCommissionLedger.affiliate_id == affiliate.id
            )
            .group_by(AffiliateCommissionLedger.currency)
        ).all()

        reserved_rows = self.db.execute(
            select(
                AffiliateWithdrawal.currency,
                func.coalesce(
                    func.sum(AffiliateWithdrawal.amount),
                    0,
                ),
            )
            .where(
                AffiliateWithdrawal.affiliate_id == affiliate.id,
                AffiliateWithdrawal.status.in_(
                    ACTIVE_WITHDRAWAL_STATES
                ),
            )
            .group_by(AffiliateWithdrawal.currency)
        ).all()

        paid_rows = self.db.execute(
            select(
                AffiliateWithdrawal.currency,
                func.coalesce(
                    func.sum(AffiliateWithdrawal.amount),
                    0,
                ),
            )
            .where(
                AffiliateWithdrawal.affiliate_id == affiliate.id,
                AffiliateWithdrawal.status == "PAID",
            )
            .group_by(AffiliateWithdrawal.currency)
        ).all()

        earnings = {
            currency: self.money(total)
            for currency, total in earnings_rows
        }

        reserved = {
            currency: self.money(total)
            for currency, total in reserved_rows
        }

        paid = {
            currency: self.money(total)
            for currency, total in paid_rows
        }

        currencies = sorted(
            set(earnings) | set(reserved) | set(paid)
        )

        result = []

        for currency in currencies:
            earned = earnings.get(currency, Decimal("0.00"))
            pending = reserved.get(currency, Decimal("0.00"))
            paid_amount = paid.get(currency, Decimal("0.00"))

            result.append(
                {
                    "currency": currency,
                    "net_earnings": earned,
                    "reserved_balance": pending,
                    "paid_balance": paid_amount,
                    "available_balance": earned - pending - paid_amount,
                }
            )

        return result

    def get_available_balance(
        self,
        affiliate: Affiliate,
        currency: str,
    ) -> Decimal:
        wallets = self.get_wallet(affiliate)

        for wallet in wallets:
            if wallet["currency"] == currency:
                available = self.money(wallet["available_balance"])

                if available < 0:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=(
                            "Wallet balance is negative. "
                            "Contact an administrator."
                        ),
                    )

                return available

        return Decimal("0.00")