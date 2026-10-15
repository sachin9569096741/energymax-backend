
"""create affiliate foundation

Revision ID: d4bf19d1043a
Revises: 2e01a699ca1b
Create Date: 2026-10-15 12:00:50.137661
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# Revision identifiers, used by Alembic.
revision: str = "d4bf19d1043a"
down_revision: Union[str, Sequence[str], None] = "2e01a699ca1b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Affiliate applications
    op.create_table(
        "affiliate_applications",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("full_name", sa.String(length=200), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=30), nullable=True),
        sa.Column("promotion_channels", sa.Text(), nullable=False),
        sa.Column("audience_description", sa.Text(), nullable=True),
        sa.Column("website_url", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("decision_reason", sa.Text(), nullable=True),
        sa.Column("reviewed_by_admin_id", sa.Integer(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "submitted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by_admin_id"],
            ["admin_users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_affiliate_applications_email",
        "affiliate_applications",
        ["email"],
        unique=False,
    )
    op.create_index(
        "ix_affiliate_applications_email_status",
        "affiliate_applications",
        ["email", "status"],
        unique=False,
    )
    op.create_index(
        "ix_affiliate_applications_public_id",
        "affiliate_applications",
        ["public_id"],
        unique=True,
    )
    op.create_index(
        "ix_affiliate_applications_status",
        "affiliate_applications",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_affiliate_applications_status_submitted",
        "affiliate_applications",
        ["status", "submitted_at"],
        unique=False,
    )
    op.create_index(
        "uq_affiliate_applications_pending_email",
        "affiliate_applications",
        ["email"],
        unique=True,
        postgresql_where=sa.text("status = 'pending'"),
        sqlite_where=sa.text("status = 'pending'"),
    )

    # Approved affiliate accounts
    op.create_table(
        "affiliates",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=True),
        sa.Column("application_id", sa.Integer(), nullable=False),
        sa.Column("full_name", sa.String(length=200), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=30), nullable=True),
        sa.Column("public_code", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("approved_by_admin_id", sa.Integer(), nullable=True),
        sa.Column(
            "approved_at",
            sa.DateTime(timezone=True),
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
            ["application_id"],
            ["affiliate_applications.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["approved_by_admin_id"],
            ["admin_users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["customers.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("application_id"),
        sa.UniqueConstraint("customer_id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("public_code"),
        sa.UniqueConstraint("public_id"),
    )

    op.create_index(
        "ix_affiliates_application_id",
        "affiliates",
        ["application_id"],
        unique=True,
    )
    op.create_index(
        "ix_affiliates_customer_id",
        "affiliates",
        ["customer_id"],
        unique=True,
    )
    op.create_index(
        "ix_affiliates_email",
        "affiliates",
        ["email"],
        unique=True,
    )
    op.create_index(
        "ix_affiliates_public_code",
        "affiliates",
        ["public_code"],
        unique=True,
    )
    op.create_index(
        "ix_affiliates_public_id",
        "affiliates",
        ["public_id"],
        unique=True,
    )
    op.create_index(
        "ix_affiliates_status",
        "affiliates",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    # Remove affiliate accounts first because they reference applications.
    op.drop_index("ix_affiliates_status", table_name="affiliates")
    op.drop_index("ix_affiliates_public_id", table_name="affiliates")
    op.drop_index("ix_affiliates_public_code", table_name="affiliates")
    op.drop_index("ix_affiliates_email", table_name="affiliates")
    op.drop_index("ix_affiliates_customer_id", table_name="affiliates")
    op.drop_index("ix_affiliates_application_id", table_name="affiliates")
    op.drop_table("affiliates")

    op.drop_index(
        "uq_affiliate_applications_pending_email",
        table_name="affiliate_applications",
    )
    op.drop_index(
        "ix_affiliate_applications_status_submitted",
        table_name="affiliate_applications",
    )
    op.drop_index(
        "ix_affiliate_applications_status",
        table_name="affiliate_applications",
    )
    op.drop_index(
        "ix_affiliate_applications_public_id",
        table_name="affiliate_applications",
    )
    op.drop_index(
        "ix_affiliate_applications_email_status",
        table_name="affiliate_applications",
    )
    op.drop_index(
        "ix_affiliate_applications_email",
        table_name="affiliate_applications",
    )
    op.drop_table("affiliate_applications")
