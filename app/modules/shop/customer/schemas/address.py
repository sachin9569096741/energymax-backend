from datetime import datetime

from pydantic import BaseModel, Field


class CustomerAddressCreateRequest(BaseModel):
    label: str = Field(min_length=1, max_length=50)
    recipient_name: str = Field(min_length=1, max_length=150)
    phone: str = Field(min_length=7, max_length=20)

    address_line1: str = Field(min_length=1, max_length=255)
    address_line2: str | None = Field(default=None, max_length=255)
    landmark: str | None = Field(default=None, max_length=255)

    city: str = Field(min_length=1, max_length=100)
    state: str = Field(min_length=1, max_length=100)
    postal_code: str = Field(min_length=3, max_length=20)
    country: str = Field(default="India", min_length=1, max_length=100)

    is_default: bool = False


class CustomerAddressUpdateRequest(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=50)
    recipient_name: str | None = Field(default=None, min_length=1, max_length=150)
    phone: str | None = Field(default=None, min_length=7, max_length=20)

    address_line1: str | None = Field(default=None, min_length=1, max_length=255)
    address_line2: str | None = Field(default=None, max_length=255)
    landmark: str | None = Field(default=None, max_length=255)

    city: str | None = Field(default=None, min_length=1, max_length=100)
    state: str | None = Field(default=None, min_length=1, max_length=100)
    postal_code: str | None = Field(default=None, min_length=3, max_length=20)
    country: str | None = Field(default=None, min_length=1, max_length=100)

    is_default: bool | None = None


class CustomerAddressResponse(BaseModel):
    public_id: str

    label: str
    recipient_name: str
    phone: str

    address_line1: str
    address_line2: str | None
    landmark: str | None

    city: str
    state: str
    postal_code: str
    country: str

    is_default: bool
    is_active: bool

    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True,
    }


class CustomerAddressListResponse(BaseModel):
    addresses: list[CustomerAddressResponse]