from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------
# CREATE
# ---------------------------------------------------------


class SubcategoryCreate(BaseModel):

    category_public_id: str = Field(
        min_length=1,
    )

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


class SubcategoryUpdate(BaseModel):

    category_public_id: str | None = Field(
        default=None,
        min_length=1,
    )

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


class SubcategoryResponse(BaseModel):

    model_config = ConfigDict(
        from_attributes=True,
    )

    public_id: str
    category_id: int

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


class SubcategoryListResponse(BaseModel):

    items: list[SubcategoryResponse]

    total: int

    page: int
    page_size: int