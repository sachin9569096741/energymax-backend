
"""create affiliate attributions

Revision ID: 4f3f67a98c4c
Revises: cd236dbc5047
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "4f3f67a98c4c"
down_revision: Union[str, Sequence[str], None] = "cd236dbc5047"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "affiliate_attributions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("affiliate_id", sa.Integer(), nullable=False),
        sa.Column("click_id", sa.Integer(), nullable=True),
        sa.Column("coupon_id", sa.Integer(), nullable=True),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column(
            "coupon_conflict",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "attributed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "policy_version",
            sa.String(length=50),
            nullable=False,
            server_default="last_click_coupon_fallback_v1",
        ),
        sa.CheckConstraint(
            "source IN ('CLICK', 'COUPON')",
            name="ck_affiliate_attributions_source",
        ),
        sa.ForeignKeyConstraint(
            ["order_id"], ["orders.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["affiliate_id"], ["affiliates.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["click_id"],
            ["affiliate_referral_clicks.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["coupon_id"], ["coupons.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_id", name="uq_affiliate_attributions_order_id"),
    )

    op.create_index(
        "ix_affiliate_attributions_affiliate_attributed",
        "affiliate_attributions",
        ["affiliate_id", "attributed_at"],
    )
    op.create_index(
        "ix_affiliate_attributions_click_id",
        "affiliate_attributions",
        ["click_id"],
    )
    op.create_index(
        "ix_affiliate_attributions_coupon_id",
        "affiliate_attributions",
        ["coupon_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_affiliate_attributions_coupon_id",
        table_name="affiliate_attributions",
    )
    op.drop_index(
        "ix_affiliate_attributions_click_id",
        table_name="affiliate_attributions",
    )
    op.drop_index(
        "ix_affiliate_attributions_affiliate_attributed",
        table_name="affiliate_attributions",
    )
    op.drop_table("affiliate_attributions")
