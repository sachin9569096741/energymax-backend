from datetime import datetime
from decimal import Decimal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)


class CouponCreate(BaseModel):
    code: str = Field(
        min_length=3,
        max_length=64,
        pattern=r"^[A-Za-z0-9_-]+$",
    )

    description: str | None = Field(
        default=None,
        max_length=2000,
    )

    discount_percent: int

    minimum_subtotal: Decimal | None = Field(
        default=None,
        ge=0,
        decimal_places=2,
    )

    max_redemptions: int | None = Field(
        default=None,
        gt=0,
    )

    max_redemptions_per_customer: int | None = Field(
        default=None,
        gt=0,
    )

    starts_at: datetime | None = None
    ends_at: datetime | None = None
    is_active: bool = True

    @model_validator(mode="after")
    def validate_coupon(self):
        if self.discount_percent not in (5, 10):
            raise ValueError(
                "discount_percent must be 5 or 10"
            )

        if (
            self.starts_at
            and self.ends_at
            and self.ends_at <= self.starts_at
        ):
            raise ValueError(
                "ends_at must be later than starts_at"
            )

        return self


class CouponUpdate(BaseModel):
    description: str | None = Field(
        default=None,
        max_length=2000,
    )

    discount_percent: int | None = None

    minimum_subtotal: Decimal | None = Field(
        default=None,
        ge=0,
        decimal_places=2,
    )

    max_redemptions: int | None = Field(
        default=None,
        gt=0,
    )

    max_redemptions_per_customer: int | None = Field(
        default=None,
        gt=0,
    )

    starts_at: datetime | None = None
    ends_at: datetime | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def validate_coupon(self):
        if (
            self.discount_percent is not None
            and self.discount_percent not in (5, 10)
        ):
            raise ValueError(
                "discount_percent must be 5 or 10"
            )

        if (
            self.starts_at
            and self.ends_at
            and self.ends_at <= self.starts_at
        ):
            raise ValueError(
                "ends_at must be later than starts_at"
            )

        return self


class CouponResponse(BaseModel):
    public_id: str
    code: str
    description: str | None
    discount_percent: int
    minimum_subtotal: Decimal | None
    max_redemptions: int | None
    max_redemptions_per_customer: int | None
    starts_at: datetime | None
    ends_at: datetime | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ApplyCouponRequest(BaseModel):
    code: str = Field(
        min_length=1,
        max_length=64,
    )


class CouponApplyResponse(BaseModel):
    checkout_public_id: str
    coupon_code: str | None
    discount_percent: int | None
    subtotal: Decimal
    discount_amount: Decimal
    shipping_amount: Decimal
    tax_amount: Decimal
    total_amount: Decimal