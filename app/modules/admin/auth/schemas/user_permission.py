from pydantic import BaseModel, Field


class UserPermissionRequest(BaseModel):
    permission_public_id: str = Field(
        min_length=1,
    )

    is_allowed: bool


class UserPermissionResponse(BaseModel):
    permission_public_id: str
    permission_name: str
    is_allowed: bool