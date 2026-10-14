"""Add coupons and coupon redemptions.

Revision ID: 2e01a699ca1b
Revises: 0f6517cb1ac3
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2e01a699ca1b"
down_revision: Union[str, Sequence[str], None] = "0f6517cb1ac3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "coupons",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("public_id", sa.String(36), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("discount_percent", sa.Integer(), nullable=False),
        sa.Column("minimum_subtotal", sa.Numeric(12, 2), nullable=True),
        sa.Column("max_redemptions", sa.Integer(), nullable=True),
        sa.Column("max_redemptions_per_customer", sa.Integer(), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
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
        sa.UniqueConstraint("public_id", name="uq_coupons_public_id"),
        sa.UniqueConstraint("code", name="uq_coupons_code"),
        sa.CheckConstraint(
            "discount_percent IN (5, 10)",
            name="ck_coupons_discount_percent",
        ),
        sa.CheckConstraint(
            "max_redemptions IS NULL OR max_redemptions > 0",
            name="ck_coupons_max_redemptions_positive",
        ),
        sa.CheckConstraint(
            "max_redemptions_per_customer IS NULL "
            "OR max_redemptions_per_customer > 0",
            name="ck_coupons_customer_limit_positive",
        ),
        sa.CheckConstraint(
            "minimum_subtotal IS NULL OR minimum_subtotal >= 0",
            name="ck_coupons_minimum_subtotal_nonnegative",
        ),
    )

    op.create_index("ix_coupons_is_active", "coupons", ["is_active"])

    op.create_table(
        "coupon_redemptions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "coupon_id",
            sa.Integer(),
            sa.ForeignKey("coupons.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "customer_id",
            sa.Integer(),
            sa.ForeignKey("customers.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "checkout_id",
            sa.Integer(),
            sa.ForeignKey("checkouts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "order_id",
            sa.Integer(),
            sa.ForeignKey("orders.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="reserved",
        ),
        sa.Column("discount_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("reserved_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("redeemed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "checkout_id",
            name="uq_coupon_redemptions_checkout",
        ),
        sa.CheckConstraint(
            "status IN ('reserved', 'redeemed', 'released')",
            name="ck_coupon_redemptions_status",
        ),
    )

    op.create_index(
        "ix_coupon_redemptions_coupon_status",
        "coupon_redemptions",
        ["coupon_id", "status"],
    )
    op.create_index(
        "ix_coupon_redemptions_customer_status",
        "coupon_redemptions",
        ["customer_id", "status"],
    )

    op.add_column(
        "checkouts",
        sa.Column("coupon_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "checkouts",
        sa.Column("coupon_code", sa.String(64), nullable=True),
    )
    op.create_foreign_key(
        "fk_checkouts_coupon_id_coupons",
        "checkouts",
        "coupons",
        ["coupon_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column(
        "orders",
        sa.Column("coupon_code", sa.String(64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("orders", "coupon_code")

    op.drop_constraint(
        "fk_checkouts_coupon_id_coupons",
        "checkouts",
        type_="foreignkey",
    )
    op.drop_column("checkouts", "coupon_code")
    op.drop_column("checkouts", "coupon_id")

    op.drop_index(
        "ix_coupon_redemptions_customer_status",
        table_name="coupon_redemptions",
    )
    op.drop_index(
        "ix_coupon_redemptions_coupon_status",
        table_name="coupon_redemptions",
    )
    op.drop_table("coupon_redemptions")

    op.drop_index("ix_coupons_is_active", table_name="coupons")
    op.drop_table("coupons")
