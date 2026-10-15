from datetime import datetime, timezone
from uuid import uuid4
from app.modules.affiliate.models.affiliate_session import AffiliateSession
from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Affiliate(Base):
    __tablename__ = "affiliates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(
        String(36), unique=True, nullable=False,
        default=lambda: str(uuid4()), index=True,
    )
    customer_id: Mapped[int | None] = mapped_column(
        ForeignKey("customers.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
        index=True,
    )
    application_id: Mapped[int] = mapped_column(
        ForeignKey("affiliate_applications.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
        index=True,
    )
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    public_code: Mapped[str] = mapped_column(
        String(32), nullable=False, unique=True, index=True
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active", index=True
    )
    approved_by_admin_id: Mapped[int | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True
    )
    approved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

        # Sprint 2: Affiliate authentication
    password_hash: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    activation_token_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        unique=True,
    )

    activation_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    activated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    application = relationship("AffiliateApplication")
    customer = relationship("Customer")
    approver = relationship("AdminUser", foreign_keys=[approved_by_admin_id])
    sessions: Mapped[list["AffiliateSession"]] = relationship(
        "AffiliateSession",
        back_populates="affiliate",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )