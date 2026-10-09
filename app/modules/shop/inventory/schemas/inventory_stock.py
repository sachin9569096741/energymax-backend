from decimal import Decimal

from pydantic import BaseModel, Field

from app.modules.shop.inventory.constants.enums import InventoryMovementType


class StockInRequest(BaseModel):
    warehouse_id: int
    variant_id: int

    quantity: Decimal = Field(
        ...,
        gt=0,
        max_digits=14,
        decimal_places=3,
    )

    movement_type: InventoryMovementType = (
        InventoryMovementType.STOCK_IN
    )

    reference_type: str | None = Field(
        default=None,
        max_length=50,
    )

    reference_id: str | None = Field(
        default=None,
        max_length=100,
    )
    idempotency_key: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Unique key used to safely retry this operation",
)
    note: str | None = Field(
        default=None,
        max_length=500,
    )


class StockOutRequest(BaseModel):
    warehouse_id: int
    variant_id: int

    quantity: Decimal = Field(
        ...,
        gt=0,
        max_digits=14,
        decimal_places=3,
    )

    movement_type: InventoryMovementType = (
        InventoryMovementType.STOCK_OUT
    )

    reference_type: str | None = Field(
        default=None,
        max_length=50,
    )

    reference_id: str | None = Field(
        default=None,
        max_length=100,
    )
    idempotency_key: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Unique key used to safely retry this operation",
)
    note: str | None = Field(
        default=None,
        max_length=500,
    )