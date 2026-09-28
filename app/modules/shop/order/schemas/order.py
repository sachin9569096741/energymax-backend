from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class OrderItemResponse(BaseModel):
    public_id: str
    product_id: int
    product_name: str
    unit_price: Decimal
    quantity: int
    subtotal: Decimal

    model_config = ConfigDict(from_attributes=True)


class OrderResponse(BaseModel):
    public_id: str
    order_number: str
    status: str

    customer_name: str
    customer_email: str | None
    customer_phone: str | None

    shipping_address_snapshot: dict

    items: list[OrderItemResponse]

    subtotal: Decimal
    discount_amount: Decimal
    shipping_amount: Decimal
    tax_amount: Decimal
    total_amount: Decimal

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


from pydantic import BaseModel, Field


class OrderStatusUpdateRequest(BaseModel):
    status: str = Field(
        ...,
        min_length=1,
        max_length=50,
    )

    note: str | None = Field(
        default=None,
        max_length=1000,
    )


from datetime import datetime

from datetime import datetime

from pydantic import BaseModel


class OrderTrackingEventResponse(BaseModel):
    status: str
    label: str
    completed: bool
    current: bool
    timestamp: datetime | None = None
    note: str | None = None


class OrderTrackingResponse(BaseModel):
    public_id: str
    order_number: str
    current_status: str
    timeline: list[OrderTrackingEventResponse]