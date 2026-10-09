"""add variant support to shop carts

Revision ID: d62cf49c25a3
Revises: d6008fa1af14
Create Date: 2026-10-08 17:00:51.220828
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d62cf49c25a3"
down_revision: Union[str, Sequence[str], None] = "d6008fa1af14"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ==========================================================
    # PRODUCT VARIANTS
    # Allow NULL flavour for products without flavours.
    # ==========================================================

    op.alter_column(
        "product_variants",
        "flavour",
        existing_type=sa.String(length=100),
        nullable=True,
    )

    # ==========================================================
    # CUSTOMER CART ITEMS
    # ==========================================================

    op.add_column(
        "customer_cart_items",
        sa.Column(
            "variant_id",
            sa.Integer(),
            nullable=True,
        ),
    )

    op.create_index(
        "ix_customer_cart_items_variant_id",
        "customer_cart_items",
        ["variant_id"],
        unique=False,
    )

    op.create_foreign_key(
        "fk_customer_cart_items_variant_id",
        "customer_cart_items",
        "product_variants",
        ["variant_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.drop_constraint(
        "uq_customer_cart_product",
        "customer_cart_items",
        type_="unique",
    )

    op.create_unique_constraint(
        "uq_customer_cart_variant",
        "customer_cart_items",
        ["cart_id", "variant_id"],
    )

    # ==========================================================
    # GUEST CART ITEMS
    # ==========================================================

    op.add_column(
        "guest_cart_items",
        sa.Column(
            "variant_id",
            sa.Integer(),
            nullable=True,
        ),
    )

    op.create_index(
        "ix_guest_cart_items_variant_id",
        "guest_cart_items",
        ["variant_id"],
        unique=False,
    )

    op.create_foreign_key(
        "fk_guest_cart_items_variant_id",
        "guest_cart_items",
        "product_variants",
        ["variant_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.drop_constraint(
        "uq_guest_cart_product",
        "guest_cart_items",
        type_="unique",
    )

    op.create_unique_constraint(
        "uq_guest_cart_variant",
        "guest_cart_items",
        ["cart_id", "variant_id"],
    )


def downgrade() -> None:
    # ==========================================================
    # GUEST CART ITEMS
    # ==========================================================

    op.drop_constraint(
        "uq_guest_cart_variant",
        "guest_cart_items",
        type_="unique",
    )

    op.create_unique_constraint(
        "uq_guest_cart_product",
        "guest_cart_items",
        ["cart_id", "product_id"],
    )

    op.drop_constraint(
        "fk_guest_cart_items_variant_id",
        "guest_cart_items",
        type_="foreignkey",
    )

    op.drop_index(
        "ix_guest_cart_items_variant_id",
        table_name="guest_cart_items",
    )

    op.drop_column(
        "guest_cart_items",
        "variant_id",
    )

    # ==========================================================
    # CUSTOMER CART ITEMS
    # ==========================================================

    op.drop_constraint(
        "uq_customer_cart_variant",
        "customer_cart_items",
        type_="unique",
    )

    op.create_unique_constraint(
        "uq_customer_cart_product",
        "customer_cart_items",
        ["cart_id", "product_id"],
    )

    op.drop_constraint(
        "fk_customer_cart_items_variant_id",
        "customer_cart_items",
        type_="foreignkey",
    )

    op.drop_index(
        "ix_customer_cart_items_variant_id",
        table_name="customer_cart_items",
    )

    op.drop_column(
        "customer_cart_items",
        "variant_id",
    )

    # ==========================================================
    # PRODUCT VARIANTS
    # ==========================================================

    op.alter_column(
        "product_variants",
        "flavour",
        existing_type=sa.String(length=100),
        nullable=False,
    )