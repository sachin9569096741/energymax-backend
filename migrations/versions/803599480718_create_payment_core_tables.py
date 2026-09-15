"""create payment core tables

Revision ID: 803599480718
Revises: bc644bbea201
Create Date: 2026-09-09 14:48:21.073899

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "803599480718"
down_revision: Union[str, Sequence[str], None] = "bc644bbea201"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # ---------------------------------------------------------
    # Payment Webhook Events
    # ---------------------------------------------------------
    op.create_table(
        "payment_webhook_events",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "public_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "provider",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "event_id",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "event_type",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "payload",
            sa.JSON(),
            nullable=False,
        ),
        sa.Column(
            "signature",
            sa.String(length=1000),
            nullable=True,
        ),
        sa.Column(
            "processed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "error_message",
            sa.String(length=1000),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "provider",
            "event_id",
            name="uq_payment_webhook_provider_event",
        ),
    )

    op.create_index(
        "ix_payment_webhook_events_created_at",
        "payment_webhook_events",
        ["created_at"],
        unique=False,
    )

    op.create_index(
        "ix_payment_webhook_events_event_type",
        "payment_webhook_events",
        ["event_type"],
        unique=False,
    )

    op.create_index(
        "ix_payment_webhook_events_provider",
        "payment_webhook_events",
        ["provider"],
        unique=False,
    )

    op.create_index(
        op.f("ix_payment_webhook_events_public_id"),
        "payment_webhook_events",
        ["public_id"],
        unique=True,
    )

    op.create_index(
        "ix_payment_webhook_events_status",
        "payment_webhook_events",
        ["status"],
        unique=False,
    )

    # ---------------------------------------------------------
    # Payments
    # ---------------------------------------------------------
    op.create_table(
        "payments",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "public_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "order_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "customer_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "amount",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
        ),
        sa.Column(
            "currency",
            sa.String(length=10),
            nullable=False,
        ),
        sa.Column(
            "provider",
            sa.String(length=50),
            nullable=True,
        ),
        sa.Column(
            "provider_order_id",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "provider_payment_id",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "status",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["customers.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["orders.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_payments_customer_id",
        "payments",
        ["customer_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_payments_order_id"),
        "payments",
        ["order_id"],
        unique=True,
    )

    op.create_index(
        "ix_payments_provider",
        "payments",
        ["provider"],
        unique=False,
    )

    op.create_index(
        op.f("ix_payments_provider_order_id"),
        "payments",
        ["provider_order_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_payments_provider_payment_id"),
        "payments",
        ["provider_payment_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_payments_public_id"),
        "payments",
        ["public_id"],
        unique=True,
    )

    op.create_index(
        op.f("ix_payments_status"),
        "payments",
        ["status"],
        unique=False,
    )

    # ---------------------------------------------------------
    # Payment Attempts
    # ---------------------------------------------------------
    op.create_table(
        "payment_attempts",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "public_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "payment_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "attempt_number",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "provider",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "amount",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
        ),
        sa.Column(
            "currency",
            sa.String(length=10),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "provider_order_id",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "provider_payment_id",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "failure_code",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column(
            "failure_message",
            sa.String(length=500),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["payment_id"],
            ["payments.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_payment_attempts_payment_id",
        "payment_attempts",
        ["payment_id"],
        unique=False,
    )

    op.create_index(
        "ix_payment_attempts_provider",
        "payment_attempts",
        ["provider"],
        unique=False,
    )

    op.create_index(
        "ix_payment_attempts_provider_order_id",
        "payment_attempts",
        ["provider_order_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_payment_attempts_provider_payment_id"),
        "payment_attempts",
        ["provider_payment_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_payment_attempts_public_id"),
        "payment_attempts",
        ["public_id"],
        unique=True,
    )

    op.create_index(
        "ix_payment_attempts_status",
        "payment_attempts",
        ["status"],
        unique=False,
    )

    # ---------------------------------------------------------
    # Payment Events
    # ---------------------------------------------------------
    op.create_table(
        "payment_events",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "public_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "payment_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "attempt_id",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "event_type",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=50),
            nullable=True,
        ),
        sa.Column(
            "message",
            sa.String(length=500),
            nullable=True,
        ),
        sa.Column(
            "event_data",
            sa.JSON(),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["attempt_id"],
            ["payment_attempts.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["payment_id"],
            ["payments.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_payment_events_attempt_id",
        "payment_events",
        ["attempt_id"],
        unique=False,
    )

    op.create_index(
        "ix_payment_events_created_at",
        "payment_events",
        ["created_at"],
        unique=False,
    )

    op.create_index(
        "ix_payment_events_event_type",
        "payment_events",
        ["event_type"],
        unique=False,
    )

    op.create_index(
        op.f("ix_payment_events_payment_id"),
        "payment_events",
        ["payment_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_payment_events_public_id"),
        "payment_events",
        ["public_id"],
        unique=True,
    )


def downgrade() -> None:
    """Downgrade schema."""

    # Payment events
    op.drop_index(
        op.f("ix_payment_events_public_id"),
        table_name="payment_events",
    )

    op.drop_index(
        op.f("ix_payment_events_payment_id"),
        table_name="payment_events",
    )

    op.drop_index(
        "ix_payment_events_event_type",
        table_name="payment_events",
    )

    op.drop_index(
        "ix_payment_events_created_at",
        table_name="payment_events",
    )

    op.drop_index(
        "ix_payment_events_attempt_id",
        table_name="payment_events",
    )

    op.drop_table("payment_events")

    # Payment attempts
    op.drop_index(
        "ix_payment_attempts_status",
        table_name="payment_attempts",
    )

    op.drop_index(
        op.f("ix_payment_attempts_public_id"),
        table_name="payment_attempts",
    )

    op.drop_index(
        op.f("ix_payment_attempts_provider_payment_id"),
        table_name="payment_attempts",
    )

    op.drop_index(
        "ix_payment_attempts_provider_order_id",
        table_name="payment_attempts",
    )

    op.drop_index(
        "ix_payment_attempts_provider",
        table_name="payment_attempts",
    )

    op.drop_index(
        "ix_payment_attempts_payment_id",
        table_name="payment_attempts",
    )

    op.drop_table("payment_attempts")

    # Payments
    op.drop_index(
        op.f("ix_payments_status"),
        table_name="payments",
    )

    op.drop_index(
        op.f("ix_payments_public_id"),
        table_name="payments",
    )

    op.drop_index(
        op.f("ix_payments_provider_payment_id"),
        table_name="payments",
    )

    op.drop_index(
        op.f("ix_payments_provider_order_id"),
        table_name="payments",
    )

    op.drop_index(
        "ix_payments_provider",
        table_name="payments",
    )

    op.drop_index(
        op.f("ix_payments_order_id"),
        table_name="payments",
    )

    op.drop_index(
        "ix_payments_customer_id",
        table_name="payments",
    )

    op.drop_table("payments")

    # Payment webhook events
    op.drop_index(
        "ix_payment_webhook_events_status",
        table_name="payment_webhook_events",
    )

    op.drop_index(
        op.f("ix_payment_webhook_events_public_id"),
        table_name="payment_webhook_events",
    )

    op.drop_index(
        "ix_payment_webhook_events_provider",
        table_name="payment_webhook_events",
    )

    op.drop_index(
        "ix_payment_webhook_events_event_type",
        table_name="payment_webhook_events",
    )

    op.drop_index(
        "ix_payment_webhook_events_created_at",
        table_name="payment_webhook_events",
    )

    op.drop_table("payment_webhook_events")