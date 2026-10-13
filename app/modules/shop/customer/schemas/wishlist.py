
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class WishlistProductResponse(BaseModel):
    public_id: str
    name: str
    slug: str
    price: Decimal
    mrp: Decimal | None = None
    primary_image_url: str | None = None


class WishlistItemResponse(BaseModel):
    public_id: str
    created_at: datetime
    product: WishlistProductResponse

    model_config = ConfigDict(from_attributes=True)


class WishlistResponse(BaseModel):
    items: list[WishlistItemResponse]
    total: int


class WishlistMessageResponse(BaseModel):
    message: str
    item: WishlistItemResponse | None = None
