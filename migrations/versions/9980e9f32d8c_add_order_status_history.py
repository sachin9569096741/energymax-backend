"""add order status history

Revision ID: 9980e9f32d8c
Revises: 483c166a3df5
Create Date: 2026-09-23 12:02:40.951219

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9980e9f32d8c"
down_revision: Union[str, Sequence[str], None] = "483c166a3df5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create order status history table."""

    op.create_table(
        "order_status_history",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "order_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "note",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "changed_by",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["orders.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_order_status_history_order_id",
        "order_status_history",
        ["order_id"],
        unique=False,
    )

    op.create_index(
        "ix_order_status_history_created_at",
        "order_status_history",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Remove order status history table."""

    op.drop_index(
        "ix_order_status_history_created_at",
        table_name="order_status_history",
    )

    op.drop_index(
        "ix_order_status_history_order_id",
        table_name="order_status_history",
    )

    op.drop_table("order_status_history")