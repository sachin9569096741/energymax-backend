from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProductImageCreate(BaseModel):
    product_id: int = Field(gt=0)

    image_url: str = Field(
        min_length=1,
        max_length=500,
    )

    alt_text: str | None = Field(
        default=None,
        max_length=255,
    )

    display_order: int = Field(
        default=0,
        ge=0,
    )

    is_primary: bool = False
    is_active: bool = True


class ProductImageUpdate(BaseModel):
    image_url: str | None = Field(
        default=None,
        min_length=1,
        max_length=500,
    )

    alt_text: str | None = Field(
        default=None,
        max_length=255,
    )

    display_order: int | None = Field(
        default=None,
        ge=0,
    )

    is_primary: bool | None = None
    is_active: bool | None = None


class ProductImageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    public_id: str
    product_id: int

    image_url: str
    cloudinary_public_id: str
    alt_text: str | None

    display_order: int
    is_primary: bool
    is_active: bool

    created_at: datetime
    updated_at: datetime


class ProductImageListResponse(BaseModel):
    items: list[ProductImageResponse]
    total: int