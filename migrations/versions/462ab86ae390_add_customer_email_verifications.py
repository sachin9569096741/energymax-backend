"""add customer email verifications

Revision ID: 462ab86ae390
Revises: 51406dca476c
Create Date: 2026-10-12 12:20:28.881635

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '462ab86ae390'
down_revision: Union[str, Sequence[str], None] = '51406dca476c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "customer_email_verifications",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["customers.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id"),
        sa.UniqueConstraint("token_hash"),
    )

    op.create_index(
        "ix_customer_email_verifications_customer_id",
        "customer_email_verifications",
        ["customer_id"],
        unique=False,
    )
    op.create_index(
        "ix_customer_email_verifications_expires_at",
        "customer_email_verifications",
        ["expires_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_customer_email_verifications_expires_at",
        table_name="customer_email_verifications",
    )
    op.drop_index(
        "ix_customer_email_verifications_customer_id",
        table_name="customer_email_verifications",
    )
    op.drop_table("customer_email_verifications")