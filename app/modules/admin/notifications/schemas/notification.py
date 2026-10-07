from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AdminNotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    public_id: str
    notification_type: str
    title: str
    message: str

    entity_type: str | None = None
    entity_public_id: str | None = None

    data: dict | None = None

    is_read: bool
    read_at: datetime | None = None
    created_at: datetime


class AdminNotificationListResponse(BaseModel):
    items: list[AdminNotificationResponse]
    total: int
    limit: int
    offset: int


class AdminNotificationUnreadCountResponse(BaseModel):
    unread_count: int


class AdminNotificationReadResponse(BaseModel):
    message: str
    notification: AdminNotificationResponse


class AdminNotificationReadAllResponse(BaseModel):
    message: str
    updated_count: int