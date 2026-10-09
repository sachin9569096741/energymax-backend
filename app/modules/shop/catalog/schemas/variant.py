from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class VariantCreate(BaseModel):

    flavour: str = Field(
        min_length=1,
        max_length=100,
    )

    sku: str = Field(
        min_length=1,
        max_length=100,
    )

    price: Decimal = Field(
        gt=0,
        max_digits=12,
        decimal_places=2,
    )

    mrp: Decimal | None = Field(
        default=None,
        gt=0,
        max_digits=12,
        decimal_places=2,
    )

    cost_price: Decimal | None = Field(
        default=None,
        gt=0,
        max_digits=12,
        decimal_places=2,
    )

    is_active: bool = True


class VariantUpdate(BaseModel):

    flavour: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )

    sku: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )

    price: Decimal | None = Field(
        default=None,
        gt=0,
        max_digits=12,
        decimal_places=2,
    )

    mrp: Decimal | None = Field(
        default=None,
        gt=0,
        max_digits=12,
        decimal_places=2,
    )

    cost_price: Decimal | None = Field(
        default=None,
        gt=0,
        max_digits=12,
        decimal_places=2,
    )

    is_active: bool | None = None


class VariantResponse(BaseModel):

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int
    public_id: str

    product_id: int

    flavour: str
    sku: str

    price: Decimal
    mrp: Decimal | None
    cost_price: Decimal | None

    is_active: bool

    created_at: datetime
    updated_at: datetime


class VariantListResponse(BaseModel):

    items: list[VariantResponse]

    total: int