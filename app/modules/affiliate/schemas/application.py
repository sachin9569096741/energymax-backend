from datetime import datetime
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    HttpUrl,
    field_validator,
)


class AffiliateApplicationCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=200)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=30)
    promotion_channels: str = Field(
        min_length=2,
        max_length=2000,
        description="Where/how you plan to promote EnergyMax",
    )
    audience_description: str | None = Field(default=None, max_length=3000)
    website_url: HttpUrl | None = None

    @field_validator("full_name", "promotion_channels", mode="before")
    @classmethod
    def strip_required_text(cls, value):
        if isinstance(value, str):
            value = value.strip()
        return value

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value):
        return value.strip().lower() if isinstance(value, str) else value


class AffiliateApplicationPublicResponse(BaseModel):
    public_id: str
    status: str
    submitted_at: datetime
    message: str = "Application received. It will be reviewed by EnergyMax."

    model_config = ConfigDict(from_attributes=True)


class AffiliateApplicationAdminResponse(BaseModel):
    public_id: str
    full_name: str
    email: EmailStr
    phone: str | None
    promotion_channels: str
    audience_description: str | None
    website_url: str | None
    status: str
    decision_reason: str | None
    submitted_at: datetime
    reviewed_at: datetime | None
    reviewed_by_admin_id: int | None

    model_config = ConfigDict(from_attributes=True)


class AffiliateApplicationDecision(BaseModel):
    decision_reason: str | None = Field(default=None, max_length=2000)


class AffiliateResponse(BaseModel):
    public_id: str
    full_name: str
    email: EmailStr
    phone: str | None
    public_code: str
    status: str
    approved_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)