"""add payment session id

Revision ID: 483c166a3df5
Revises: ec9bc5764f12
Create Date: 2026-09-21 10:56:52.741851

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "483c166a3df5"
down_revision: Union[str, Sequence[str], None] = "ec9bc5764f12"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "payments",
        sa.Column(
            "payment_session_id",
            sa.String(length=500),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_payments_payment_session_id",
        "payments",
        ["payment_session_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_payments_payment_session_id",
        table_name="payments",
    )
    op.drop_column(
        "payments",
        "payment_session_id",
    )