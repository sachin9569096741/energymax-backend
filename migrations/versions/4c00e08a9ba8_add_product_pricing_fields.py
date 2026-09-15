"""add product pricing fields

Revision ID: 4c00e08a9ba8
Revises: 60787ad0b6a7
Create Date: 2026-08-31 11:04:06.331864

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4c00e08a9ba8"

down_revision: Union[str, Sequence[str], None] = "60787ad0b6a7"

branch_labels: Union[str, Sequence[str], None] = None

depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # ---------------------------------------------------------
    # PRICE
    # ---------------------------------------------------------
    # Existing products already exist in the database.
    # Therefore, temporarily use 0.00 so the NOT NULL
    # constraint can be added safely.
    op.add_column(
        "products",
        sa.Column(
            "price",
            sa.Numeric(
                precision=12,
                scale=2,
            ),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )

    # ---------------------------------------------------------
    # MRP
    # ---------------------------------------------------------

    op.add_column(
        "products",
        sa.Column(
            "mrp",
            sa.Numeric(
                precision=12,
                scale=2,
            ),
            nullable=True,
        ),
    )

    # ---------------------------------------------------------
    # COST PRICE
    # ---------------------------------------------------------

    op.add_column(
        "products",
        sa.Column(
            "cost_price",
            sa.Numeric(
                precision=12,
                scale=2,
            ),
            nullable=True,
        ),
    )

    # ---------------------------------------------------------
    # REMOVE TEMPORARY DEFAULT
    # ---------------------------------------------------------
    # New products must explicitly provide their price.
    op.alter_column(
        "products",
        "price",
        server_default=None,
    )


def downgrade() -> None:
    """Downgrade schema."""

    # ---------------------------------------------------------
    # REMOVE COST PRICE
    # ---------------------------------------------------------

    op.drop_column(
        "products",
        "cost_price",
    )

    # ---------------------------------------------------------
    # REMOVE MRP
    # ---------------------------------------------------------

    op.drop_column(
        "products",
        "mrp",
    )

    # ---------------------------------------------------------
    # REMOVE PRICE
    # ---------------------------------------------------------

    op.drop_column(
        "products",
        "price",
    )