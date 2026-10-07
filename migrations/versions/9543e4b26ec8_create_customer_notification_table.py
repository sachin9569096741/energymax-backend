"""create customer notification table

Revision ID: 9543e4b26ec8
Revises: 55a29336718f
Create Date: 2026-10-07 11:20:04.213851

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9543e4b26ec8"
down_revision: Union[str, Sequence[str], None] = "55a29336718f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    op.create_table(
        "customer_notifications",

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
            "customer_id",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "notification_type",
            sa.String(length=50),
            nullable=False,
        ),

        sa.Column(
            "title",
            sa.String(length=255),
            nullable=False,
        ),

        sa.Column(
            "message",
            sa.Text(),
            nullable=False,
        ),

        sa.Column(
            "entity_type",
            sa.String(length=50),
            nullable=True,
        ),

        sa.Column(
            "entity_public_id",
            sa.String(length=36),
            nullable=True,
        ),

        sa.Column(
            "data",
            sa.JSON(),
            nullable=True,
        ),

        sa.Column(
            "is_read",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),

        sa.Column(
            "read_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),

        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),

        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["customers.id"],
            ondelete="CASCADE",
        ),

        sa.PrimaryKeyConstraint("id"),

        sa.UniqueConstraint(
            "public_id",
            name="uq_customer_notifications_public_id",
        ),
    )

    # Customer + unread/read filtering
    op.create_index(
        "ix_customer_notifications_customer_read",
        "customer_notifications",
        ["customer_id", "is_read"],
    )

    # Customer notification history ordering
    op.create_index(
        "ix_customer_notifications_customer_created",
        "customer_notifications",
        ["customer_id", "created_at"],
    )

    # Notification type filtering
    op.create_index(
        "ix_customer_notifications_type",
        "customer_notifications",
        ["notification_type"],
    )

    # Entity lookup
    op.create_index(
        "ix_customer_notifications_entity",
        "customer_notifications",
        ["entity_type", "entity_public_id"],
    )


def downgrade() -> None:

    op.drop_index(
        "ix_customer_notifications_entity",
        table_name="customer_notifications",
    )

    op.drop_index(
        "ix_customer_notifications_type",
        table_name="customer_notifications",
    )

    op.drop_index(
        "ix_customer_notifications_customer_created",
        table_name="customer_notifications",
    )

    op.drop_index(
        "ix_customer_notifications_customer_read",
        table_name="customer_notifications",
    )

    op.drop_table("customer_notifications")