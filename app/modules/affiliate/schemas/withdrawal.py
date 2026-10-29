from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class WithdrawalCreate(BaseModel):
    amount: Decimal = Field(
        gt=0,
        max_digits=12,
        decimal_places=2,
    )
    currency: str = Field(min_length=3, max_length=3)
    idempotency_key: str = Field(min_length=8, max_length=150)

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        value = value.strip().upper()

        if len(value) != 3 or not value.isalpha():
            raise ValueError("Currency must be a three-letter code.")

        return value


class WithdrawalReject(BaseModel):
    reason: str = Field(min_length=5, max_length=500)

    @field_validator("reason")
    @classmethod
    def normalize_reason(cls, value: str) -> str:
        return value.strip()


class WithdrawalMarkPaid(BaseModel):
    payout_reference: str = Field(min_length=3, max_length=150)

    @field_validator("payout_reference")
    @classmethod
    def normalize_reference(cls, value: str) -> str:
        return value.strip()


class WithdrawalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    public_id: str
    affiliate_id: int
    amount: Decimal
    currency: str
    status: str
    payout_reference: str | None
    rejection_reason: str | None
    requested_at: datetime
    reviewed_at: datetime | None
    reviewed_by_admin_id: int | None
    paid_at: datetime | None
    provider: str | None
    provider_reference: str | None
    beneficiary_reference: str | None
    payment_initiated_at: datetime | None
    failure_reason: str | None
    last_provider_status: str | None
    created_at: datetime
    updated_at: datetime



class WithdrawalStartProcessing(BaseModel):
    provider: str = Field(min_length=2, max_length=30)
    beneficiary_reference: str = Field(min_length=3, max_length=150)

    @field_validator("provider")
    @classmethod
    def normalize_provider(cls, value: str) -> str:
        value = value.strip().upper()

        if not value:
            raise ValueError("Provider is required.")

        return value

    @field_validator("beneficiary_reference")
    @classmethod
    def normalize_beneficiary_reference(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Beneficiary reference is required.")

        return value