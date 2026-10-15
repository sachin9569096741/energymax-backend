import uuid

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AffiliateApplication(Base):
    __tablename__ = "affiliate_applications"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(
        String(36), unique=True, index=True,
        default=lambda: str(uuid.uuid4()),
        nullable=False,
    )
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    promotion_channels: Mapped[str] = mapped_column(Text, nullable=False)
    audience_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    website_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", index=True
    )
    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by_admin_id: Mapped[int | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[object | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    submitted_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
        onupdate=func.now(), nullable=False
    )

    reviewer = relationship("AdminUser", foreign_keys=[reviewed_by_admin_id])

    __table_args__ = (
        Index(
            "ix_affiliate_applications_status_submitted",
            "status", "submitted_at",
        ),
        Index(
            "ix_affiliate_applications_email_status",
            "email", "status",
        ),
        Index(
            "uq_affiliate_applications_pending_email",
            "email",
            unique=True,
            postgresql_where=(status == "pending"),
            sqlite_where=(status == "pending"),
        ),
    )