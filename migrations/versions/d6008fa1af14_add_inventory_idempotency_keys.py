"""add inventory idempotency keys

Revision ID: d6008fa1af14
Revises: a1b2907e1bc3
Create Date: 2026-10-08 13:02:27.262679

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d6008fa1af14"
down_revision: Union[str, Sequence[str], None] = "a1b2907e1bc3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # --------------------------------------------------------------
    # INVENTORY MOVEMENTS
    # --------------------------------------------------------------

    op.add_column(
        "inventory_movements",
        sa.Column(
            "idempotency_key",
            sa.String(length=100),
            nullable=True,
        ),
    )

    op.create_index(
        op.f("ix_inventory_movements_idempotency_key"),
        "inventory_movements",
        ["idempotency_key"],
        unique=True,
    )

    # --------------------------------------------------------------
    # INVENTORY RESERVATIONS
    # --------------------------------------------------------------

    op.add_column(
        "inventory_reservations",
        sa.Column(
            "idempotency_key",
            sa.String(length=100),
            nullable=True,
        ),
    )

    op.create_index(
        op.f("ix_inventory_reservations_idempotency_key"),
        "inventory_reservations",
        ["idempotency_key"],
        unique=True,
    )

    # --------------------------------------------------------------
    # STOCK ADJUSTMENTS
    # --------------------------------------------------------------

    op.add_column(
        "stock_adjustments",
        sa.Column(
            "idempotency_key",
            sa.String(length=100),
            nullable=True,
        ),
    )

    op.create_index(
        op.f("ix_stock_adjustments_idempotency_key"),
        "stock_adjustments",
        ["idempotency_key"],
        unique=True,
    )


def downgrade() -> None:
    """Downgrade schema."""

    # --------------------------------------------------------------
    # STOCK ADJUSTMENTS
    # --------------------------------------------------------------

    op.drop_index(
        op.f("ix_stock_adjustments_idempotency_key"),
        table_name="stock_adjustments",
    )

    op.drop_column(
        "stock_adjustments",
        "idempotency_key",
    )

    # --------------------------------------------------------------
    # INVENTORY RESERVATIONS
    # --------------------------------------------------------------

    op.drop_index(
        op.f("ix_inventory_reservations_idempotency_key"),
        table_name="inventory_reservations",
    )

    op.drop_column(
        "inventory_reservations",
        "idempotency_key",
    )

    # --------------------------------------------------------------
    # INVENTORY MOVEMENTS
    # --------------------------------------------------------------

    op.drop_index(
        op.f("ix_inventory_movements_idempotency_key"),
        table_name="inventory_movements",
    )

    op.drop_column(
        "inventory_movements",
        "idempotency_key",
    )