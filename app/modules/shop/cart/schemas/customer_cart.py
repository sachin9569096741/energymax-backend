from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class CustomerCartItemAddRequest(BaseModel):
    product_public_id: str = Field(min_length=1, max_length=36)
    quantity: int = Field(gt=0, le=100)


class CustomerCartItemUpdateRequest(BaseModel):
    quantity: int = Field(gt=0, le=100)


class CustomerCartItemResponse(BaseModel):
    public_id: str
    product_public_id: str
    quantity: int
    unit_price: Decimal

    model_config = {"from_attributes": True}


class CustomerCartResponse(BaseModel):
    public_id: str
    items: list[CustomerCartItemResponse]
    total_items: int
    subtotal: Decimal
    created_at: datetime
    updated_at: datetime