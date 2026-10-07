from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AdminNotification(Base):
    __tablename__ = "admin_notifications"

    __table_args__ = (
        Index(
            "ix_admin_notifications_admin_user_read",
            "admin_user_id",
            "is_read",
        ),
        Index(
            "ix_admin_notifications_admin_user_created",
            "admin_user_id",
            "created_at",
        ),
        Index(
            "ix_admin_notifications_notification_type",
            "notification_type",
        ),
        Index(
            "ix_admin_notifications_entity",
            "entity_type",
            "entity_public_id",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    public_id: Mapped[str] = mapped_column(
        String(36),
        unique=True,
        nullable=False,
        index=True,
        default=lambda: str(uuid4()),
    )

    admin_user_id: Mapped[int] = mapped_column(
        ForeignKey(
            "admin_users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    notification_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    entity_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    entity_public_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
        index=True,
    )

    data: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    is_read: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
    )

    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    admin_user = relationship(
        "AdminUser",
        foreign_keys=[admin_user_id],
    )