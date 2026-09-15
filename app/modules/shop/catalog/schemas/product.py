from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.modules.shop.catalog.schemas.product_image import (
    ProductImageResponse,
)


# ---------------------------------------------------------
# CREATE
# ---------------------------------------------------------


class ProductCreate(BaseModel):

    subcategory_id: int = Field(
        gt=0,
    )

    name: str = Field(
        min_length=1,
        max_length=200,
    )

    slug: str = Field(
        min_length=1,
        max_length=220,
    )

    short_description: str | None = Field(
        default=None,
        max_length=500,
    )

    description: str | None = None

    brand_name: str | None = Field(
        default=None,
        max_length=150,
    )

    price: Decimal = Field(
        gt=0,
        max_digits=12,
        decimal_places=2,
    )

    mrp: Decimal | None = Field(
        default=None,
        gt=0,
        max_digits=12,
        decimal_places=2,
    )

    cost_price: Decimal | None = Field(
        default=None,
        gt=0,
        max_digits=12,
        decimal_places=2,
    )

    seo_title: str | None = Field(
        default=None,
        max_length=200,
    )

    seo_description: str | None = Field(
        default=None,
        max_length=500,
    )

    is_active: bool = True

    is_featured: bool = False

    display_order: int = Field(
        default=0,
        ge=0,
    )


# ---------------------------------------------------------
# UPDATE
# ---------------------------------------------------------


class ProductUpdate(BaseModel):

    subcategory_id: int | None = Field(
        default=None,
        gt=0,
    )

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
    )

    slug: str | None = Field(
        default=None,
        min_length=1,
        max_length=220,
    )

    short_description: str | None = Field(
        default=None,
        max_length=500,
    )

    description: str | None = None

    brand_name: str | None = Field(
        default=None,
        max_length=150,
    )

    price: Decimal | None = Field(
        default=None,
        gt=0,
        max_digits=12,
        decimal_places=2,
    )

    mrp: Decimal | None = Field(
        default=None,
        gt=0,
        max_digits=12,
        decimal_places=2,
    )

    cost_price: Decimal | None = Field(
        default=None,
        gt=0,
        max_digits=12,
        decimal_places=2,
    )

    seo_title: str | None = Field(
        default=None,
        max_length=200,
    )

    seo_description: str | None = Field(
        default=None,
        max_length=500,
    )

    is_active: bool | None = None

    is_featured: bool | None = None

    display_order: int | None = Field(
        default=None,
        ge=0,
    )


# ---------------------------------------------------------
# RESPONSE
# ---------------------------------------------------------


class ProductResponse(BaseModel):

    model_config = ConfigDict(
        from_attributes=True,
    )
    id: int
    public_id: str

    subcategory_id: int

    name: str

    slug: str

    short_description: str | None

    description: str | None

    brand_name: str | None

    price: Decimal

    mrp: Decimal | None

    seo_title: str | None

    seo_description: str | None

    is_active: bool

    is_featured: bool

    display_order: int

    published_at: datetime | None

    created_at: datetime

    updated_at: datetime

    images: list[ProductImageResponse] = Field(
        default_factory=list,
    )


# ---------------------------------------------------------
# LIST RESPONSE
# ---------------------------------------------------------


class ProductListResponse(BaseModel):

    items: list[ProductResponse]

    total: int

    page: int

    page_size: int