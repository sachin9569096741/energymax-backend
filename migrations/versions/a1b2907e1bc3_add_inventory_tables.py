"""add inventory tables

Revision ID: a1b2907e1bc3
Revises: dfbd97ef242b
Create Date: 2026-10-07 16:14:52.239603

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1b2907e1bc3"
down_revision: Union[str, Sequence[str], None] = "dfbd97ef242b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # ------------------------------------------------------------------
    # INVENTORY BALANCES
    # ------------------------------------------------------------------

    op.create_table(
        "inventory_balances",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "warehouse_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "variant_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "on_hand",
            sa.Numeric(precision=14, scale=3),
            nullable=False,
        ),
        sa.Column(
            "reserved",
            sa.Numeric(precision=14, scale=3),
            nullable=False,
        ),
        sa.Column(
            "damaged",
            sa.Numeric(precision=14, scale=3),
            nullable=False,
        ),
        sa.Column(
            "incoming",
            sa.Numeric(precision=14, scale=3),
            nullable=False,
        ),
        sa.Column(
            "reorder_level",
            sa.Numeric(precision=14, scale=3),
            nullable=False,
        ),
        sa.Column(
            "reorder_quantity",
            sa.Numeric(precision=14, scale=3),
            nullable=False,
        ),
        sa.Column(
            "safety_stock",
            sa.Numeric(precision=14, scale=3),
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
            ["variant_id"],
            ["product_variants.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["warehouse_id"],
            ["warehouses.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "warehouse_id",
            "variant_id",
            name="uq_inventory_balance_warehouse_variant",
        ),
    )

    op.create_index(
        op.f("ix_inventory_balances_variant_id"),
        "inventory_balances",
        ["variant_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_inventory_balances_warehouse_id"),
        "inventory_balances",
        ["warehouse_id"],
        unique=False,
    )

    # ------------------------------------------------------------------
    # INVENTORY MOVEMENTS
    # ------------------------------------------------------------------

    op.create_table(
        "inventory_movements",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "warehouse_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "variant_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "movement_type",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "quantity",
            sa.Numeric(precision=14, scale=3),
            nullable=False,
        ),
        sa.Column(
            "before_quantity",
            sa.Numeric(precision=14, scale=3),
            nullable=False,
        ),
        sa.Column(
            "after_quantity",
            sa.Numeric(precision=14, scale=3),
            nullable=False,
        ),
        sa.Column(
            "reference_type",
            sa.String(length=50),
            nullable=True,
        ),
        sa.Column(
            "reference_id",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column(
            "note",
            sa.String(length=500),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["variant_id"],
            ["product_variants.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["warehouse_id"],
            ["warehouses.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_inventory_movements_created_at"),
        "inventory_movements",
        ["created_at"],
        unique=False,
    )

    op.create_index(
        op.f("ix_inventory_movements_movement_type"),
        "inventory_movements",
        ["movement_type"],
        unique=False,
    )

    op.create_index(
        op.f("ix_inventory_movements_reference_id"),
        "inventory_movements",
        ["reference_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_inventory_movements_reference_type"),
        "inventory_movements",
        ["reference_type"],
        unique=False,
    )

    op.create_index(
        op.f("ix_inventory_movements_variant_id"),
        "inventory_movements",
        ["variant_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_inventory_movements_warehouse_id"),
        "inventory_movements",
        ["warehouse_id"],
        unique=False,
    )

    # ------------------------------------------------------------------
    # INVENTORY RESERVATIONS
    # ------------------------------------------------------------------

    op.create_table(
        "inventory_reservations",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "warehouse_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "variant_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "quantity",
            sa.Numeric(precision=14, scale=3),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=30),
            nullable=False,
        ),
        sa.Column(
            "reference_type",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "reference_id",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
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
            ["variant_id"],
            ["product_variants.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["warehouse_id"],
            ["warehouses.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_inventory_reservations_expires_at"),
        "inventory_reservations",
        ["expires_at"],
        unique=False,
    )

    op.create_index(
        op.f("ix_inventory_reservations_reference_id"),
        "inventory_reservations",
        ["reference_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_inventory_reservations_reference_type"),
        "inventory_reservations",
        ["reference_type"],
        unique=False,
    )

    op.create_index(
        op.f("ix_inventory_reservations_status"),
        "inventory_reservations",
        ["status"],
        unique=False,
    )

    op.create_index(
        op.f("ix_inventory_reservations_variant_id"),
        "inventory_reservations",
        ["variant_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_inventory_reservations_warehouse_id"),
        "inventory_reservations",
        ["warehouse_id"],
        unique=False,
    )

    # ------------------------------------------------------------------
    # STOCK ADJUSTMENTS
    # ------------------------------------------------------------------

    op.create_table(
        "stock_adjustments",
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
            "warehouse_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "variant_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "adjustment_type",
            sa.String(length=30),
            nullable=False,
        ),
        sa.Column(
            "quantity",
            sa.Numeric(precision=14, scale=3),
            nullable=False,
        ),
        sa.Column(
            "reason",
            sa.String(length=500),
            nullable=False,
        ),
        sa.Column(
            "before_quantity",
            sa.Numeric(precision=14, scale=3),
            nullable=False,
        ),
        sa.Column(
            "after_quantity",
            sa.Numeric(precision=14, scale=3),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["variant_id"],
            ["product_variants.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["warehouse_id"],
            ["warehouses.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_stock_adjustments_public_id"),
        "stock_adjustments",
        ["public_id"],
        unique=True,
    )

    op.create_index(
        op.f("ix_stock_adjustments_variant_id"),
        "stock_adjustments",
        ["variant_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_stock_adjustments_warehouse_id"),
        "stock_adjustments",
        ["warehouse_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""

    # ------------------------------------------------------------------
    # STOCK ADJUSTMENTS
    # ------------------------------------------------------------------

    op.drop_index(
        op.f("ix_stock_adjustments_warehouse_id"),
        table_name="stock_adjustments",
    )

    op.drop_index(
        op.f("ix_stock_adjustments_variant_id"),
        table_name="stock_adjustments",
    )

    op.drop_index(
        op.f("ix_stock_adjustments_public_id"),
        table_name="stock_adjustments",
    )

    op.drop_table("stock_adjustments")

    # ------------------------------------------------------------------
    # INVENTORY RESERVATIONS
    # ------------------------------------------------------------------

    op.drop_index(
        op.f("ix_inventory_reservations_warehouse_id"),
        table_name="inventory_reservations",
    )

    op.drop_index(
        op.f("ix_inventory_reservations_variant_id"),
        table_name="inventory_reservations",
    )

    op.drop_index(
        op.f("ix_inventory_reservations_status"),
        table_name="inventory_reservations",
    )

    op.drop_index(
        op.f("ix_inventory_reservations_reference_type"),
        table_name="inventory_reservations",
    )

    op.drop_index(
        op.f("ix_inventory_reservations_reference_id"),
        table_name="inventory_reservations",
    )

    op.drop_index(
        op.f("ix_inventory_reservations_expires_at"),
        table_name="inventory_reservations",
    )

    op.drop_table("inventory_reservations")

    # ------------------------------------------------------------------
    # INVENTORY MOVEMENTS
    # ------------------------------------------------------------------

    op.drop_index(
        op.f("ix_inventory_movements_warehouse_id"),
        table_name="inventory_movements",
    )

    op.drop_index(
        op.f("ix_inventory_movements_variant_id"),
        table_name="inventory_movements",
    )

    op.drop_index(
        op.f("ix_inventory_movements_reference_type"),
        table_name="inventory_movements",
    )

    op.drop_index(
        op.f("ix_inventory_movements_reference_id"),
        table_name="inventory_movements",
    )

    op.drop_index(
        op.f("ix_inventory_movements_movement_type"),
        table_name="inventory_movements",
    )

    op.drop_index(
        op.f("ix_inventory_movements_created_at"),
        table_name="inventory_movements",
    )

    op.drop_table("inventory_movements")

    # ------------------------------------------------------------------
    # INVENTORY BALANCES
    # ------------------------------------------------------------------

    op.drop_index(
        op.f("ix_inventory_balances_warehouse_id"),
        table_name="inventory_balances",
    )

    op.drop_index(
        op.f("ix_inventory_balances_variant_id"),
        table_name="inventory_balances",
    )

    op.drop_table("inventory_balances")