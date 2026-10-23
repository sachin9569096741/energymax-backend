from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CommissionPolicyCreate(BaseModel):
    affiliate_public_id: str | None = Field(
        default=None,
        description="Leave null for the global default policy.",
    )
    commission_rate: Decimal = Field(
        gt=0,
        le=100,
        max_digits=7,
        decimal_places=4,
        examples=["10.0000"],
    )
    effective_from: datetime
    effective_until: datetime | None = None

    @model_validator(mode="after")
    def validate_dates(self):
        if (
            self.effective_from.tzinfo is None
            or self.effective_from.utcoffset() is None
        ):
            raise ValueError("effective_from must include a timezone.")

        if self.effective_until is not None:
            if (
                self.effective_until.tzinfo is None
                or self.effective_until.utcoffset() is None
            ):
                raise ValueError(
                    "effective_until must include a timezone."
                )

            if self.effective_until <= self.effective_from:
                raise ValueError(
                    "effective_until must be later than effective_from."
                )

        return self


class CommissionPolicyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    public_id: str
    affiliate_id: int | None
    commission_rate: Decimal
    is_active: bool
    effective_from: datetime
    effective_until: datetime | None
    created_by_admin_id: int
    created_at: datetime
    updated_at: datetime