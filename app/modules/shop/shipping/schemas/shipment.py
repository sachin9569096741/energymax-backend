
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ShipmentCreateRequest(BaseModel):
    length_cm: Decimal = Field(gt=0, le=200)
    breadth_cm: Decimal = Field(gt=0, le=200)
    height_cm: Decimal = Field(gt=0, le=200)
    weight_kg: Decimal = Field(gt=0, le=100)


class ShipmentResponse(BaseModel):
    id: int
    order_id: int
    shiprocket_order_id: str | None
    shiprocket_shipment_id: str | None
    awb_code: str | None
    courier_name: str | None
    status: str
    tracking_url: str | None
    length_cm: Decimal
    breadth_cm: Decimal
    height_cm: Decimal
    weight_kg: Decimal
    created_at: object
    updated_at: object

    model_config = ConfigDict(from_attributes=True)
