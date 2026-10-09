"""add product variants

Revision ID: 783fd370ba30
Revises: 9543e4b26ec8
Create Date: 2026-10-07 15:03:06.164119

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "783fd370ba30"
down_revision: Union[str, Sequence[str], None] = "9543e4b26ec8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create product variants table."""

    op.create_table(
        "product_variants",

        # Primary key
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),

        # Public identifier
        sa.Column(
            "public_id",
            sa.String(length=36),
            nullable=False,
        ),

        # Parent product
        sa.Column(
            "product_id",
            sa.Integer(),
            nullable=False,
        ),

        # Variant information
        sa.Column(
            "flavour",
            sa.String(length=100),
            nullable=False,
        ),

        # Unique SKU
        sa.Column(
            "sku",
            sa.String(length=100),
            nullable=False,
        ),

        # Pricing
        sa.Column(
            "price",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
        ),

        sa.Column(
            "mrp",
            sa.Numeric(precision=12, scale=2),
            nullable=True,
        ),

        sa.Column(
            "cost_price",
            sa.Numeric(precision=12, scale=2),
            nullable=True,
        ),

        # Status
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
        ),

        # Timestamps
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

        # Constraints
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            ondelete="CASCADE",
        ),

        sa.PrimaryKeyConstraint("id"),

        sa.UniqueConstraint("sku"),
    )

    # ------------------------------------------------------------------
    # Indexes
    # ------------------------------------------------------------------

    op.create_index(
        op.f("ix_product_variants_is_active"),
        "product_variants",
        ["is_active"],
        unique=False,
    )

    op.create_index(
        "ix_product_variants_product_active",
        "product_variants",
        ["product_id", "is_active"],
        unique=False,
    )

    op.create_index(
        op.f("ix_product_variants_product_id"),
        "product_variants",
        ["product_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_product_variants_public_id"),
        "product_variants",
        ["public_id"],
        unique=True,
    )

    # NOTE:
    # We intentionally do NOT create a separate non-unique SKU index.
    # SKU already has a UNIQUE constraint.


def downgrade() -> None:
    """Drop product variants table."""

    op.drop_index(
        op.f("ix_product_variants_public_id"),
        table_name="product_variants",
    )

    op.drop_index(
        op.f("ix_product_variants_product_id"),
        table_name="product_variants",
    )

    op.drop_index(
        "ix_product_variants_product_active",
        table_name="product_variants",
    )

    op.drop_index(
        op.f("ix_product_variants_is_active"),
        table_name="product_variants",
    )

    op.drop_table("product_variants")