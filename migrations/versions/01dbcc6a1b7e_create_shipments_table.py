
"""create shipments table

Revision ID: 01dbcc6a1b7e
Revises: 0f9b4089ab42
Create Date: 2026-10-15 17:31:21.301883
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "01dbcc6a1b7e"
down_revision: Union[str, Sequence[str], None] = "0f9b4089ab42"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "shipments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("shiprocket_order_id", sa.String(length=100), nullable=True),
        sa.Column("shiprocket_shipment_id", sa.String(length=100), nullable=True),
        sa.Column("awb_code", sa.String(length=100), nullable=True),
        sa.Column("courier_name", sa.String(length=255), nullable=True),
        sa.Column(
            "status",
            sa.String(length=50),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("tracking_url", sa.Text(), nullable=True),
        sa.Column("length_cm", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("breadth_cm", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("height_cm", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("weight_kg", sa.Numeric(precision=10, scale=3), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["orders.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_id", name="uq_shipments_order_id"),
    )

    op.create_index(
        "ix_shipments_created_at",
        "shipments",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_shipments_status",
        "shipments",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_shipments_status", table_name="shipments")
    op.drop_index("ix_shipments_created_at", table_name="shipments")
    op.drop_table("shipments")
