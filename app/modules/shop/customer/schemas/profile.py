from pydantic import BaseModel, EmailStr, Field


class CustomerProfileUpdateRequest(BaseModel):
    first_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )

    last_name: str | None = Field(
        default=None,
        max_length=100,
    )

    email: EmailStr | None = None

    phone: str | None = Field(
        default=None,
        min_length=7,
        max_length=20,
    )


class CustomerProfileResponse(BaseModel):
    public_id: str
    username: str

    first_name: str
    last_name: str | None

    email: EmailStr | None
    phone: str | None

    email_verified: bool
    phone_verified: bool

    is_active: bool

    created_at: object
    updated_at: object

    model_config = {
        "from_attributes": True,
    }