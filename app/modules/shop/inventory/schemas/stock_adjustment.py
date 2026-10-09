from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, ConfigDict

from app.modules.shop.inventory.constants.enums import (
    StockAdjustmentType,
)


# ------------------------------------------------------------------
# CREATE ADJUSTMENT
# ------------------------------------------------------------------

class StockAdjustmentCreateRequest(BaseModel):
    warehouse_id: str = Field(
        ...,
        min_length=1,
        description="Warehouse public UUID",
    )

    variant_id: str = Field(
        ...,
        min_length=1,
        description="Product variant public UUID",
    )

    adjustment_type: StockAdjustmentType

    quantity: Decimal = Field(
        ...,
        gt=0,
        max_digits=14,
        decimal_places=3,
    )

    reason: str = Field(
        ...,
        min_length=1,
        max_length=500,
    )

    idempotency_key: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Unique key used to safely retry this operation",
    )


# ------------------------------------------------------------------
# RESPONSE
# ------------------------------------------------------------------

class StockAdjustmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    public_id: str

    warehouse_id: int
    variant_id: int

    adjustment_type: str

    quantity: Decimal

    reason: str

    before_quantity: Decimal
    after_quantity: Decimal

    created_at: datetime


# ------------------------------------------------------------------
# LIST RESPONSE
# ------------------------------------------------------------------

class StockAdjustmentListResponse(BaseModel):
    items: list[StockAdjustmentResponse]
    total: int