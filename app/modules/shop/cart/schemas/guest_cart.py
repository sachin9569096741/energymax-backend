from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field


class GuestCartItemAdd(BaseModel):
    product_public_id: str = Field(min_length=1)
    quantity: int = Field(gt=0, le=100)


class GuestCartItemUpdate(BaseModel):
    quantity: int = Field(gt=0, le=100)


class GuestCartItemResponse(BaseModel):
    public_id: str
    product_public_id: str
    product_name: str
    quantity: int
    unit_price: Decimal
    subtotal: Decimal


class GuestCartResponse(BaseModel):
    public_id: str
    guest_cart_token: str | None = None
    items: list[GuestCartItemResponse]
    total_items: int
    total_amount: Decimal
    expires_at: datetime