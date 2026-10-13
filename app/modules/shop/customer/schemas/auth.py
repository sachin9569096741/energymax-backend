from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, model_validator


class CustomerRegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)

    email: EmailStr | None = None
    phone: str | None = Field(default=None, min_length=7, max_length=20)

    password: str = Field(min_length=8, max_length=128)

    @model_validator(mode="after")
    def validate_contact(self):
        if not self.email and not self.phone:
            raise ValueError("Either email or phone is required.")
        return self


class CustomerLoginRequest(BaseModel):
    identifier: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=128)


class CustomerOTPRequest(BaseModel):
    destination: str = Field(min_length=1, max_length=255)
    channel: str = Field(min_length=1, max_length=20)
    purpose: str = Field(min_length=1, max_length=50)


class CustomerOTPVerifyRequest(BaseModel):
    destination: str = Field(min_length=1, max_length=255)
    channel: str = Field(min_length=1, max_length=20)
    purpose: str = Field(min_length=1, max_length=50)
    code: str = Field(min_length=4, max_length=10)


class CustomerResponse(BaseModel):
    public_id: str
    username: str
    first_name: str
    last_name: str | None
    email: EmailStr | None
    phone: str | None
    email_verified: bool
    phone_verified: bool
    is_active: bool
    last_login_at: datetime | None
    created_at: datetime

    model_config = {
        "from_attributes": True,
    }


class CustomerAuthResponse(BaseModel):
    customer: CustomerResponse
    session_token: str


class CustomerOTPResponse(BaseModel):
    message: str
    expires_at: datetime | None = None


class CustomerRegistrationResponse(BaseModel):
    message: str
    customer: CustomerResponse
    email: EmailStr
    verification_required: bool = True
    expires_at: datetime


class ForgotPasswordRequest(BaseModel):
    method: str = Field(
        pattern="^(username|email|phone)$"
    )
    identifier: str = Field(
        min_length=1,
        max_length=255,
    )


class ForgotPasswordConfirmOTPRequest(ForgotPasswordRequest):
    code: str = Field(
        min_length=6,
        max_length=6,
        pattern="^[0-9]{6}$",
    )


class ForgotPasswordResetRequest(BaseModel):
    reset_token: str = Field(
        min_length=20,
        max_length=200,
    )
    new_password: str = Field(
        min_length=8,
        max_length=128,
    )


class ForgotPasswordOTPResponse(BaseModel):
    message: str


class ForgotPasswordConfirmOTPResponse(BaseModel):
    message: str
    reset_token: str
    expires_at: datetime