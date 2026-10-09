from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class StockOperationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    warehouse_id: int
    variant_id: int

    on_hand: Decimal
    reserved: Decimal
    damaged: Decimal
    available: Decimal

    movement_id: int
    movement_type: str
    movement_quantity: Decimal

    before_quantity: Decimal
    after_quantity: Decimal

    created_at: datetime