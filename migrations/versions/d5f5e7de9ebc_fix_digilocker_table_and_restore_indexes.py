
"""Fix DigiLocker table and restore indexes.

Revision ID: d5f5e7de9ebc
Revises: a26e8f14732d
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d5f5e7de9ebc"
down_revision: Union[str, Sequence[str], None] = "a26e8f14732d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Restore uniqueness for orders.public_id.
    op.drop_index(
        "ix_orders_public_id",
        table_name="orders",
    )
    op.create_index(
        "ix_orders_public_id",
        "orders",
        ["public_id"],
        unique=True,
    )

    # Keep customer_carts.customer_id non-unique.
    # This permits multiple carts for the same customer.
    op.drop_index(
        "ix_customer_carts_customer_id",
        table_name="customer_carts",
    )
    op.create_index(
        "ix_customer_carts_customer_id",
        "customer_carts",
        ["customer_id"],
        unique=False,
    )

    # Create the DigiLocker verification table.
    op.create_table(
        "affiliate_digilocker_verifications",
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
            "affiliate_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "verification_id",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "provider_reference_id",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column(
            "status",
            sa.String(length=30),
            nullable=False,
            server_default="initiated",
        ),
        sa.Column(
            "document_type",
            sa.String(length=30),
            nullable=False,
            server_default="AADHAAR",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["affiliate_id"],
            ["affiliates.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "public_id",
            name="uq_affiliate_digilocker_verifications_public_id",
        ),
        sa.UniqueConstraint(
            "verification_id",
            name="uq_affiliate_digilocker_verification_id",
        ),
    )

    op.create_index(
        "ix_affiliate_digilocker_verifications_affiliate_id",
        "affiliate_digilocker_verifications",
        ["affiliate_id"],
        unique=False,
    )

    op.create_index(
        "ix_affiliate_digilocker_verifications_status",
        "affiliate_digilocker_verifications",
        ["status"],
        unique=False,
    )

    op.create_index(
        "ix_digilocker_affiliate_status",
        "affiliate_digilocker_verifications",
        ["affiliate_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    # Remove DigiLocker indexes and table.
    op.drop_index(
        "ix_digilocker_affiliate_status",
        table_name="affiliate_digilocker_verifications",
    )

    op.drop_index(
        "ix_affiliate_digilocker_verifications_status",
        table_name="affiliate_digilocker_verifications",
    )

    op.drop_index(
        "ix_affiliate_digilocker_verifications_affiliate_id",
        table_name="affiliate_digilocker_verifications",
    )

    op.drop_table("affiliate_digilocker_verifications")

    # Restore the non-unique customer cart index.
    op.drop_index(
        "ix_customer_carts_customer_id",
        table_name="customer_carts",
    )

    op.create_index(
        "ix_customer_carts_customer_id",
        "customer_carts",
        ["customer_id"],
        unique=False,
    )

    # Restore the index state before this migration.
    op.drop_index(
        "ix_orders_public_id",
        table_name="orders",
    )

    op.create_index(
        "ix_orders_public_id",
        "orders",
        ["public_id"],
        unique=False,
    )
