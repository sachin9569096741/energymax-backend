"""add order confirmation email tracking

Revision ID: 51406dca476c
Revises: 62f26380063b
Create Date: 2026-10-10 13:50:31.982673

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '51406dca476c'
down_revision: Union[str, Sequence[str], None] = '62f26380063b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column(
            "confirmation_email_sent_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column(
        "orders",
        "confirmation_email_sent_at",
    )