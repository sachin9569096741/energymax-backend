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


class CustomerNotification(Base):
    __tablename__ = "customer_notifications"

    __table_args__ = (
    Index(
        "ix_customer_notifications_customer_read",
        "customer_id",
        "is_read",
    ),
    Index(
        "ix_customer_notifications_customer_created",
        "customer_id",
        "created_at",
    ),
    Index(
        "ix_customer_notifications_type",
        "notification_type",
    ),
    Index(
        "ix_customer_notifications_entity",
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

        default=lambda: str(uuid4()),
    )

    customer_id: Mapped[int] = mapped_column(
        ForeignKey(
            "customers.id",
            ondelete="CASCADE",
        ),
        nullable=False,

    )

    notification_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,

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

    )

    data: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    is_read: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,

    )

    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),

    )

    customer = relationship(
        "Customer",
        foreign_keys=[customer_id],
    )
