from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class CommissionLedgerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    public_id: str
    affiliate_id: int
    attribution_id: int
    order_id: int
    entry_type: str
    amount: Decimal
    currency: str
    base_amount: Decimal
    commission_rate: Decimal
    idempotency_key: str
    reverses_entry_id: int | None = None
    description: str | None = None
    created_at: datetime


class AffiliateEarningsResponse(BaseModel):
    currency: str
    total_commissions: Decimal
    total_reversals: Decimal
    total_adjustments: Decimal
    net_earnings: Decimal
    commission_count: int