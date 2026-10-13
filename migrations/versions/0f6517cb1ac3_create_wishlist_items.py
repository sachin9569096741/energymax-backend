
"""create wishlist items

Revision ID: 0f6517cb1ac3
Revises: 462ab86ae390
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0f6517cb1ac3"
down_revision: Union[str, Sequence[str], None] = "462ab86ae390"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "wishlist_items",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["customers.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "public_id",
            name="uq_wishlist_items_public_id",
        ),
        sa.UniqueConstraint(
            "customer_id",
            "product_id",
            name="uq_wishlist_customer_product",
        ),
    )

    op.create_index(
        "ix_wishlist_customer_created",
        "wishlist_items",
        ["customer_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_wishlist_customer_created",
        table_name="wishlist_items",
    )
    op.drop_table("wishlist_items")
