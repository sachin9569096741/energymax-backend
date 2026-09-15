from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AdminSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    public_id: str
    expires_at: datetime
    revoked_at: datetime | None = None
    last_used_at: datetime | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    created_at: datetime
    updated_at: datetime