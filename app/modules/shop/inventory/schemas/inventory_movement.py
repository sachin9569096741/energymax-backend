from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


# ------------------------------------------------------------------
# MOVEMENT RESPONSE
# ------------------------------------------------------------------

class InventoryMovementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int

    # Product
    product_id: int
    product_name: str

    # Variant
    variant_id: int
    flavour: str
    sku: str

    # Warehouse
    warehouse_id: int
    warehouse_name: str
    warehouse_code: str

    # Movement
    movement_type: str

    quantity: Decimal
    before_quantity: Decimal
    after_quantity: Decimal

    # Reference
    reference_type: str | None = None
    reference_id: str | None = None

    # Additional information
    note: str | None = None

    created_at: datetime


# ------------------------------------------------------------------
# MOVEMENT LIST RESPONSE
# ------------------------------------------------------------------

class InventoryMovementListResponse(BaseModel):
    items: list[InventoryMovementResponse]
    total: int