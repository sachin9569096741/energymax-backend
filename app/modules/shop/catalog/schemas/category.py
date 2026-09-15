from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------
# CREATE
# ---------------------------------------------------------


class CategoryCreate(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=100,
    )

    slug: str = Field(
        min_length=1,
        max_length=120,
    )

    description: str | None = None

    image_url: str | None = Field(
        default=None,
        max_length=500,
    )

    display_order: int = Field(
        default=0,
        ge=0,
    )

    is_active: bool = True


# ---------------------------------------------------------
# UPDATE
# ---------------------------------------------------------


class CategoryUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )

    slug: str | None = Field(
        default=None,
        min_length=1,
        max_length=120,
    )

    description: str | None = None

    image_url: str | None = Field(
        default=None,
        max_length=500,
    )

    display_order: int | None = Field(
        default=None,
        ge=0,
    )

    is_active: bool | None = None


# ---------------------------------------------------------
# RESPONSE
# ---------------------------------------------------------


class CategoryResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    public_id: str

    name: str
    slug: str

    description: str | None
    image_url: str | None

    display_order: int
    is_active: bool

    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------
# LIST RESPONSE
# ---------------------------------------------------------


class CategoryListResponse(BaseModel):
    items: list[CategoryResponse]

    total: int

    page: int
    page_size: int