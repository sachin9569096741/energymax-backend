
"""add affiliate authentication and sessions

Revision ID: 0f9b4089ab42
Revises: d4bf19d1043a
Create Date: 2026-10-15 12:45:32.128441
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0f9b4089ab42"
down_revision: Union[str, Sequence[str], None] = "d4bf19d1043a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add authentication fields to existing affiliates.
    op.add_column(
        "affiliates",
        sa.Column("password_hash", sa.String(500), nullable=True),
    )
    op.add_column(
        "affiliates",
        sa.Column(
            "activation_token_hash",
            sa.String(64),
            nullable=True,
        ),
    )
    op.add_column(
        "affiliates",
        sa.Column(
            "activation_expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "affiliates",
        sa.Column(
            "activated_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "affiliates",
        sa.Column(
            "last_login_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    op.create_unique_constraint(
        "uq_affiliates_activation_token_hash",
        "affiliates",
        ["activation_token_hash"],
    )

    # Create database-backed affiliate sessions.
    op.create_table(
        "affiliate_sessions",
        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("public_id", sa.String(36), nullable=False),
        sa.Column("affiliate_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "last_used_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "revoked_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["affiliate_id"],
            ["affiliates.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "public_id",
            name="uq_affiliate_sessions_public_id",
        ),
        sa.UniqueConstraint(
            "token_hash",
            name="uq_affiliate_sessions_token_hash",
        ),
    )

    op.create_index(
        "ix_affiliate_sessions_affiliate_id",
        "affiliate_sessions",
        ["affiliate_id"],
    )
    op.create_index(
        "ix_affiliate_sessions_affiliate_active",
        "affiliate_sessions",
        ["affiliate_id", "is_active"],
    )
    op.create_index(
        "ix_affiliate_sessions_expires_at",
        "affiliate_sessions",
        ["expires_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_affiliate_sessions_expires_at",
        table_name="affiliate_sessions",
    )
    op.drop_index(
        "ix_affiliate_sessions_affiliate_active",
        table_name="affiliate_sessions",
    )
    op.drop_index(
        "ix_affiliate_sessions_affiliate_id",
        table_name="affiliate_sessions",
    )

    op.drop_table("affiliate_sessions")

    op.drop_constraint(
        "uq_affiliates_activation_token_hash",
        "affiliates",
        type_="unique",
    )

    op.drop_column("affiliates", "last_login_at")
    op.drop_column("affiliates", "activated_at")
    op.drop_column("affiliates", "activation_expires_at")
    op.drop_column("affiliates", "activation_token_hash")
    op.drop_column("affiliates", "password_hash")
