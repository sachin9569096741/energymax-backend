"""add shipment operation states

Revision ID: 3a6c9e1d4b72
Revises: e796f0226b5f
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "3a6c9e1d4b72"
down_revision: Union[str, Sequence[str], None] = "e796f0226b5f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for column in (
        "awb_operation_status",
        "pickup_operation_status",
        "label_operation_status",
        "manifest_operation_status",
    ):
        op.add_column(
            "shipments",
            sa.Column(
                column,
                sa.String(length=30),
                nullable=False,
                server_default="idle",
            ),
        )


def downgrade() -> None:
    for column in (
        "manifest_operation_status",
        "label_operation_status",
        "pickup_operation_status",
        "awb_operation_status",
    ):
        op.drop_column("shipments", column)
