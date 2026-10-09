
"""add variant to checkout items

Revision ID: 22bd966739b9
Revises: d62cf49c25a3
Create Date: 2026-10-09 10:02:41.649948
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "22bd966739b9"
down_revision: Union[str, Sequence[str], None] = "d62cf49c25a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "checkout_items",
        sa.Column("variant_id", sa.Integer(), nullable=True),
    )

    op.create_foreign_key(
        "fk_checkout_items_variant_id_product_variants",
        "checkout_items",
        "product_variants",
        ["variant_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.create_index(
        "ix_checkout_items_variant_id",
        "checkout_items",
        ["variant_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_checkout_items_variant_id",
        table_name="checkout_items",
    )

    op.drop_constraint(
        "fk_checkout_items_variant_id_product_variants",
        "checkout_items",
        type_="foreignkey",
    )

    op.drop_column("checkout_items", "variant_id")
