from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CustomerNotificationResponse(BaseModel):
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

    model_config = ConfigDict(
        from_attributes=True
    )


class CustomerNotificationListResponse(BaseModel):
    items: list[CustomerNotificationResponse]

    total: int
    limit: int
    offset: int


class CustomerNotificationUnreadCountResponse(BaseModel):
    unread_count: int


class CustomerNotificationReadAllResponse(BaseModel):
    updated_count: int


class CustomerNotificationReadResponse(BaseModel):
    notification: CustomerNotificationResponse