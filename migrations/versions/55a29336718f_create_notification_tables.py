"""create admin notification table

Revision ID: 55a29336718f
Revises: 9980e9f32d8c
Create Date: 2026-10-01 15:15:17.653240
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "55a29336718f"
down_revision: Union[str, Sequence[str], None] = "9980e9f32d8c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "admin_notifications",

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
            "admin_user_id",
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
        ),

        sa.ForeignKeyConstraint(
            ["admin_user_id"],
            ["admin_users.id"],
            ondelete="CASCADE",
        ),

        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_admin_notifications_public_id",
        "admin_notifications",
        ["public_id"],
        unique=True,
    )

    op.create_index(
        "ix_admin_notifications_admin_user_id",
        "admin_notifications",
        ["admin_user_id"],
        unique=False,
    )

    op.create_index(
        "ix_admin_notifications_admin_user_read",
        "admin_notifications",
        ["admin_user_id", "is_read"],
        unique=False,
    )

    op.create_index(
        "ix_admin_notifications_admin_user_created",
        "admin_notifications",
        ["admin_user_id", "created_at"],
        unique=False,
    )

    op.create_index(
        "ix_admin_notifications_notification_type",
        "admin_notifications",
        ["notification_type"],
        unique=False,
    )

    op.create_index(
        "ix_admin_notifications_is_read",
        "admin_notifications",
        ["is_read"],
        unique=False,
    )

    op.create_index(
        "ix_admin_notifications_created_at",
        "admin_notifications",
        ["created_at"],
        unique=False,
    )

    op.create_index(
        "ix_admin_notifications_entity",
        "admin_notifications",
        ["entity_type", "entity_public_id"],
        unique=False,
    )

    op.create_index(
        "ix_admin_notifications_entity_public_id",
        "admin_notifications",
        ["entity_public_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_admin_notifications_entity_public_id",
        table_name="admin_notifications",
    )

    op.drop_index(
        "ix_admin_notifications_entity",
        table_name="admin_notifications",
    )

    op.drop_index(
        "ix_admin_notifications_created_at",
        table_name="admin_notifications",
    )

    op.drop_index(
        "ix_admin_notifications_is_read",
        table_name="admin_notifications",
    )

    op.drop_index(
        "ix_admin_notifications_notification_type",
        table_name="admin_notifications",
    )

    op.drop_index(
        "ix_admin_notifications_admin_user_created",
        table_name="admin_notifications",
    )

    op.drop_index(
        "ix_admin_notifications_admin_user_read",
        table_name="admin_notifications",
    )

    op.drop_index(
        "ix_admin_notifications_admin_user_id",
        table_name="admin_notifications",
    )

    op.drop_index(
        "ix_admin_notifications_public_id",
        table_name="admin_notifications",
    )

    op.drop_table("admin_notifications")