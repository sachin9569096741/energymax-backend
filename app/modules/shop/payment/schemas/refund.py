from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class RefundRequest(BaseModel):
    amount: Decimal | None = Field(
        default=None,
        gt=0,
        max_digits=12,
        decimal_places=2,
        description="Refund amount. Omit for a full refund.",
    )

    reason: str | None = Field(
        default=None,
        max_length=500,
    )


class RefundResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    public_id: str
    payment_id: int
    amount: Decimal
    currency: str
    status: str
    provider: str
    provider_refund_id: str | None = None
    idempotency_key: str
    reason: str | None = None
    failure_code: str | None = None
    failure_message: str | None = None