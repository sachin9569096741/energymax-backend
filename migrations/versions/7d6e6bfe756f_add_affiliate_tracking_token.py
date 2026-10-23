
"""Add affiliate tracking token hash.

Revision ID: 7d6e6bfe756f
Revises: 4f3f67a98c4c
Create Date: 2026-10-22 15:18:32.870625
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# Revision identifiers used by Alembic.
revision: str = "7d6e6bfe756f"
down_revision: Union[str, Sequence[str], None] = "4f3f67a98c4c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add a nullable, unique referral tracking token hash."""
    op.add_column(
        "affiliate_referral_clicks",
        sa.Column(
            "tracking_token_hash",
            sa.String(length=64),
            nullable=True,
        ),
    )

    op.create_index(
        "ix_affiliate_referral_clicks_tracking_token_hash",
        "affiliate_referral_clicks",
        ["tracking_token_hash"],
        unique=True,
    )


def downgrade() -> None:
    """Remove the affiliate referral tracking token hash."""
    op.drop_index(
        "ix_affiliate_referral_clicks_tracking_token_hash",
        table_name="affiliate_referral_clicks",
    )

    op.drop_column(
        "affiliate_referral_clicks",
        "tracking_token_hash",
    )
