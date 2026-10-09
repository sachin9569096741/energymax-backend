from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class InventoryBalanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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

    # Inventory
    on_hand: Decimal
    reserved: Decimal
    damaged: Decimal
    incoming: Decimal
    available: Decimal

    # Reorder configuration
    reorder_level: Decimal
    reorder_quantity: Decimal
    safety_stock: Decimal

    created_at: datetime
    updated_at: datetime


class InventoryBalanceListResponse(BaseModel):
    items: list[InventoryBalanceResponse]
    total: int