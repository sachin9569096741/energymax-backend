from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AdminUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    public_id: str
    username: str
    staff_type: str
    is_super_admin: bool
    is_active: bool
    role_id: int | None = None
    last_login_at: datetime | None = None
    created_at: datetime
    updated_at: datetime