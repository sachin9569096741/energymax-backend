from pydantic import BaseModel, Field
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class AdminOrderListItemResponse(BaseModel):
    public_id: str
    order_number: str

    customer_name: str
    customer_email: str | None = None
    customer_phone: str | None = None

    status: str

    subtotal: Decimal
    discount_amount: Decimal
    shipping_amount: Decimal
    tax_amount: Decimal
    total_amount: Decimal

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminOrderListResponse(BaseModel):
    items: list[AdminOrderListItemResponse]

    page: int
    page_size: int
    total: int
    total_pages: int

class AdminOrderStatusUpdateRequest(BaseModel):
    status: str = Field(
        ...,
        min_length=1,
        max_length=50,
    )

    note: str | None = Field(
        default=None,
        max_length=1000,
    )