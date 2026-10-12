from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, ConfigDict


class ReservationCreateRequest(BaseModel):
    warehouse_id: str = Field(
        ...,
        description="Public UUID of the warehouse",
    )

    variant_id: str = Field(
        ...,
        description="Public UUID of the product variant",
    )

    quantity: Decimal = Field(
        ...,
        gt=0,
        max_digits=14,
        decimal_places=3,
    )

    reference_type: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Reference type, e.g. ORDER",
    )

    reference_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Reference identifier, e.g. order ID",
    )

    idempotency_key: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Unique key used to safely retry the reservation",
    )


class ReservationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: int
    warehouse_id: int
    variant_id: int
    quantity: Decimal
    status: str
    reference_type: str
    reference_id: str
    expires_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ReservationListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: list[ReservationResponse]
    total: int
