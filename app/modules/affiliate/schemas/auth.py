from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class AffiliateLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)
    captcha_token: str = Field(min_length=1, max_length=4096)


class AffiliateActivateRequest(BaseModel):
    token: str = Field(min_length=20, max_length=256)
    new_password: str = Field(min_length=8, max_length=128)
    captcha_token: str = Field(min_length=1, max_length=4096)


class AffiliateMeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    public_id: str
    full_name: str
    email: EmailStr
    phone: str | None = None
    public_code: str
    status: str
    approved_at: datetime
    activated_at: datetime | None = None
    last_login_at: datetime | None = None


class AffiliateSessionResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    affiliate: AffiliateMeResponse


class AffiliateMessageResponse(BaseModel):
    message: str