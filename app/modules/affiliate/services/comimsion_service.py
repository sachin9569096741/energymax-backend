from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.affiliate.models.affiliate import Affiliate
from app.modules.affiliate.models.affiliate_attribution import (
    AffiliateAttribution,
)
from app.modules.affiliate.models.affiliate_commission_ledger import (
    AffiliateCommissionLedger,
)
from app.modules.affiliate.models.affiliate_commision_policy import (
    AffiliateCommissionPolicy,
)


CENT = Decimal("0.01")


class CommissionError(Exception):
    """Base exception for affiliate commission operations."""


class CommissionEligibilityError(CommissionError):
    """The affiliate or order is not eligible for commission."""


class CommissionPolicyError(CommissionError):
    """No applicable commission policy exists."""


class CommissionIdempotencyConflict(CommissionError):
    """An idempotency key was reused for a different operation."""


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    """Normalize a database datetime for timezone-aware comparisons."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class CommissionService:
    def __init__(self, db: Session):
        self.db = db

    def get_policy(
        self,
        affiliate_id: int,
        *,
        now: datetime | None = None,
    ) -> AffiliateCommissionPolicy:
        """
        Return the applicable Admin-created percentage policy.

        A valid affiliate-specific policy takes precedence over
        the global default.
        """
        now = now or _utc_now()

        policies = self.db.scalars(
            select(AffiliateCommissionPolicy)
            .where(
                AffiliateCommissionPolicy.is_active.is_(True),
                AffiliateCommissionPolicy.effective_from <= now,
                (
                    AffiliateCommissionPolicy.effective_until.is_(None)
                    | (AffiliateCommissionPolicy.effective_until > now)
                ),
                AffiliateCommissionPolicy.affiliate_id.in_(
                    [affiliate_id]
                )
                | AffiliateCommissionPolicy.affiliate_id.is_(None),
            )
            .order_by(
                AffiliateCommissionPolicy.affiliate_id.is_(None),
                AffiliateCommissionPolicy.effective_from.desc(),
                AffiliateCommissionPolicy.id.desc(),
            )
        ).all()

        # Affiliate-specific policy first, then global default.
        for policy in policies:
            if policy.affiliate_id == affiliate_id:
                return policy

        for policy in policies:
            if policy.affiliate_id is None:
                return policy

        raise CommissionPolicyError(
            "No active commission policy applies to this affiliate."
        )

    def calculate_commission(
        self,
        *,
        eligible_amount: Decimal,
        commission_rate: Decimal,
    ) -> Decimal:
        """
        Calculate commission from a trusted, server-derived eligible
        amount. Never pass an amount directly from the affiliate UI.
        """
        eligible_amount = Decimal(eligible_amount)
        commission_rate = Decimal(commission_rate)

        if not eligible_amount.is_finite() or eligible_amount < 0:
            raise CommissionError("Eligible amount must be non-negative.")

        if (
            not commission_rate.is_finite()
            or commission_rate <= 0
            or commission_rate > 100
        ):
            raise CommissionError("Commission rate must be between 0 and 100.")

        return (
            eligible_amount * commission_rate / Decimal("100")
        ).quantize(CENT, rounding=ROUND_HALF_UP)

    def create_commission(
        self,
        *,
        order_id: int,
        eligible_amount: Decimal,
        idempotency_key: str,
        currency: str = "INR",
        description: str | None = None,
        now: datetime | None = None,
    ) -> AffiliateCommissionLedger:
        """
        Create one commission for an existing final attribution.

        The caller must supply eligible_amount from a trusted,
        server-side calculation. The caller owns commit/rollback.
        """
        now = now or _utc_now()

        if not idempotency_key or not idempotency_key.strip():
            raise CommissionError("An idempotency key is required.")

        idempotency_key = idempotency_key.strip()

        if len(idempotency_key) > 150:
            raise CommissionError(
                "Idempotency key cannot exceed 150 characters."
            )

        currency = currency.strip().upper()

        if len(currency) != 3 or not currency.isalpha():
            raise CommissionError(
                "Currency must be a three-letter currency code."
            )

        # A retry should return the existing entry only if its financial
        # inputs match the original request.
        existing = self.db.scalar(
            select(AffiliateCommissionLedger).where(
                AffiliateCommissionLedger.idempotency_key
                == idempotency_key
            )
        )

        if existing is not None:
            attribution = self.db.scalar(
                select(AffiliateAttribution).where(
                    AffiliateAttribution.order_id == order_id
                )
            )

            if attribution is None:
                raise CommissionEligibilityError(
                    "No affiliate attribution exists for this order."
                )

            policy = self.get_policy(attribution.affiliate_id, now=now)

            expected_amount = self.calculate_commission(
                eligible_amount=eligible_amount,
                commission_rate=policy.commission_rate,
            )

            same_operation = (
                existing.entry_type == "COMMISSION"
                and existing.order_id == order_id
                and existing.affiliate_id == attribution.affiliate_id
                and existing.attribution_id == attribution.id
                and existing.base_amount == Decimal(eligible_amount)
                and existing.commission_rate == policy.commission_rate
                and existing.amount == expected_amount
                and existing.currency == currency
            )

            if not same_operation:
                raise CommissionIdempotencyConflict(
                    "The idempotency key was already used with "
                    "different commission inputs."
                )

            return existing

        attribution = self.db.scalar(
            select(AffiliateAttribution).where(
                AffiliateAttribution.order_id == order_id
            )
        )

        if attribution is None:
            raise CommissionEligibilityError(
                "No affiliate attribution exists for this order."
            )

        affiliate = self.db.scalar(
            select(Affiliate).where(
                Affiliate.id == attribution.affiliate_id
            )
        )

        if affiliate is None:
            raise CommissionEligibilityError(
                "The attributed affiliate does not exist."
            )

        if (
            affiliate.status != "active"
            or affiliate.activated_at is None
        ):
            raise CommissionEligibilityError(
                "The affiliate is not active and activated."
            )

        # Do not award a second commission for the same order.
        order_commission = self.db.scalar(
            select(AffiliateCommissionLedger).where(
                AffiliateCommissionLedger.order_id == order_id,
                AffiliateCommissionLedger.entry_type == "COMMISSION",
            )
        )

        if order_commission is not None:
            raise CommissionIdempotencyConflict(
                "A commission already exists for this order."
            )

        policy = self.get_policy(attribution.affiliate_id, now=now)

        eligible_amount = Decimal(eligible_amount)

        if not eligible_amount.is_finite() or eligible_amount < 0:
            raise CommissionError("Eligible amount must be non-negative.")

        commission_amount = self.calculate_commission(
            eligible_amount=eligible_amount,
            commission_rate=policy.commission_rate,
        )

        entry = AffiliateCommissionLedger(
            affiliate_id=attribution.affiliate_id,
            attribution_id=attribution.id,
            order_id=order_id,
            entry_type="COMMISSION",
            amount=commission_amount,
            currency=currency,
            base_amount=eligible_amount.quantize(
                CENT,
                rounding=ROUND_HALF_UP,
            ),
            commission_rate=policy.commission_rate,
            idempotency_key=idempotency_key,
            description=description,
            created_at=now,
        )

        self.db.add(entry)
        self.db.flush()

        return entry