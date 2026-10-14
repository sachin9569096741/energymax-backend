from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class CheckoutAddressRequest(BaseModel):
    address_public_id: str = Field(min_length=1, max_length=36)


class CheckoutItemResponse(BaseModel):
    public_id: str
    product_id: int
    variant_id: int | None = None
    product_name: str
    unit_price: Decimal
    quantity: int
    subtotal: Decimal

    model_config = ConfigDict(from_attributes=True)


class CheckoutResponse(BaseModel):
    public_id: str
    status: str

    selected_address_id: int | None

    items: list[CheckoutItemResponse]

    subtotal: Decimal
    discount_amount: Decimal
    shipping_amount: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    coupon_code: str | None
    expires_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)