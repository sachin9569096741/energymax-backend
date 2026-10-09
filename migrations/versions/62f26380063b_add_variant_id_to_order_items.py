
"""add variant_id to order_items

Revision ID: 62f26380063b
Revises: 9cfb15585359
"""

from alembic import op
import sqlalchemy as sa

revision = "62f26380063b"
down_revision = "9cfb15585359"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "order_items",
        sa.Column("variant_id", sa.Integer(), nullable=True),
    )

    op.create_foreign_key(
        "fk_order_items_variant_id_product_variants",
        "order_items",
        "product_variants",
        ["variant_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.create_index(
        "ix_order_items_variant_id",
        "order_items",
        ["variant_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_order_items_variant_id",
        table_name="order_items",
    )

    op.drop_constraint(
        "fk_order_items_variant_id_product_variants",
        "order_items",
        type_="foreignkey",
    )

    op.drop_column("order_items", "variant_id")
