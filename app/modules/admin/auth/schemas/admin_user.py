from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# =========================================================
# CREATE STAFF
# =========================================================


class AdminUserCreate(BaseModel):
    username: str = Field(
        min_length=3,
        max_length=100,
    )

    password: str = Field(
        min_length=8,
        max_length=128,
    )

    staff_type: str = Field(
        min_length=2,
        max_length=100,
    )

    role_name: str | None = Field(
    default=None,
    min_length=2,
    max_length=100,
)

    is_active: bool = True


# =========================================================
# UPDATE STAFF
# =========================================================


class AdminUserUpdate(BaseModel):
    username: str | None = Field(
        default=None,
        min_length=3,
        max_length=100,
    )

    staff_type: str | None = Field(
        default=None,
        min_length=2,
        max_length=100,
    )

    role_public_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=36,
    )

    is_active: bool | None = None


# =========================================================
# CHANGE PASSWORD
# =========================================================


class AdminUserPasswordUpdate(BaseModel):
    password: str = Field(
        min_length=8,
        max_length=128,
    )


# =========================================================
# STAFF RESPONSE
# =========================================================


class AdminUserResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    public_id: str
    username: str
    staff_type: str
    is_super_admin: bool
    is_active: bool

    role_id: int | None

    last_login_at: datetime | None

    created_at: datetime
    updated_at: datetime