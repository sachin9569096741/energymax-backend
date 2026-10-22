
"""add affiliate referral click tracking

Revision ID: cd236dbc5047
Revises: 3a6c9e1d4b72
Create Date: 2026-10-19 14:50:15.223565
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "cd236dbc5047"
down_revision: Union[str, Sequence[str], None] = "3a6c9e1d4b72"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create affiliate referral click tracking table."""

    op.create_table(
        "affiliate_referral_clicks",
        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "affiliate_id",
            sa.Integer(),
            sa.ForeignKey("affiliates.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "visitor_hash",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "user_agent",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "referrer",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "clicked_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_index(
        "ix_affiliate_referral_clicks_affiliate_id",
        "affiliate_referral_clicks",
        ["affiliate_id"],
        unique=False,
    )

    op.create_index(
        "ix_affiliate_referral_clicks_visitor_hash",
        "affiliate_referral_clicks",
        ["visitor_hash"],
        unique=False,
    )

    op.create_index(
        "ix_affiliate_referral_clicks_clicked_at",
        "affiliate_referral_clicks",
        ["clicked_at"],
        unique=False,
    )

    op.create_index(
        "ix_affiliate_referral_clicks_affiliate_clicked_at",
        "affiliate_referral_clicks",
        ["affiliate_id", "clicked_at"],
        unique=False,
    )


def downgrade() -> None:
    """Drop affiliate referral click tracking table."""

    op.drop_index(
        "ix_affiliate_referral_clicks_affiliate_clicked_at",
        table_name="affiliate_referral_clicks",
    )

    op.drop_index(
        "ix_affiliate_referral_clicks_clicked_at",
        table_name="affiliate_referral_clicks",
    )

    op.drop_index(
        "ix_affiliate_referral_clicks_visitor_hash",
        table_name="affiliate_referral_clicks",
    )

    op.drop_index(
        "ix_affiliate_referral_clicks_affiliate_id",
        table_name="affiliate_referral_clicks",
    )

    op.drop_table("affiliate_referral_clicks")
