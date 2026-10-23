from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


class CommissionAdjustmentRequest(BaseModel):
    amount: Decimal = Field(
        description="Signed adjustment amount in the original currency.",
        max_digits=12,
        decimal_places=2,
    )
    currency: str = Field(min_length=3, max_length=3)
    description: str = Field(min_length=5, max_length=500)
    idempotency_key: str = Field(min_length=8, max_length=150)

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, value: Decimal) -> Decimal:
        if not value.is_finite() or value == 0:
            raise ValueError("Adjustment amount must be finite and non-zero.")
        return value

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        value = value.strip().upper()
        if len(value) != 3 or not value.isalpha():
            raise ValueError("Currency must be a three-letter currency code.")
        return value

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 5:
            raise ValueError("Please provide a meaningful description.")
        return value


class CommissionReversalRequest(BaseModel):
    reason: str = Field(min_length=5, max_length=500)
    idempotency_key: str = Field(min_length=8, max_length=150)

    @field_validator("reason")
    @classmethod
    def normalize_reason(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 5:
            raise ValueError("Please provide a meaningful reversal reason.")
        return value