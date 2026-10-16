"""add pickup and shipping document fields

Revision ID: e796f0226b5f
Revises: 01dbcc6a1b7e
Create Date: 2026-10-16 10:30:36.398595

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e796f0226b5f'
down_revision: Union[str, Sequence[str], None] = '01dbcc6a1b7e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def upgrade() -> None:
    op.add_column(
        "shipments",
        sa.Column(
            "pickup_token_number",
            sa.String(length=255),
            nullable=True,
        ),
    )
    op.add_column(
        "shipments",
        sa.Column(
            "pickup_scheduled_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "shipments",
        sa.Column(
            "label_url",
            sa.Text(),
            nullable=True,
        ),
    )
    op.add_column(
        "shipments",
        sa.Column(
            "manifest_url",
            sa.Text(),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("shipments", "manifest_url")
    op.drop_column("shipments", "label_url")
    op.drop_column("shipments", "pickup_scheduled_at")
    op.drop_column("shipments", "pickup_token_number")
