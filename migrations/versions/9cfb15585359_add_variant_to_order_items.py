"""add variant to order items

Revision ID: 9cfb15585359
Revises: 22bd966739b9
Create Date: 2026-10-09 10:50:38.506092

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9cfb15585359'
down_revision: Union[str, Sequence[str], None] = '22bd966739b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
