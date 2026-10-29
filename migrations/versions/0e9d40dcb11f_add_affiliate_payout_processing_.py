"""add affiliate payout processing lifecycle

Revision ID: 0e9d40dcb11f
Revises: 3337ee4310ac
Create Date: 2026-10-27 17:19:58.897793
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# Revision identifiers, used by Alembic.
revision: str = "0e9d40dcb11f"
down_revision: Union[str, Sequence[str], None] = "3337ee4310ac"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Update the allowed withdrawal statuses.
    op.drop_constraint(
        "ck_affiliate_withdrawal_status",
        "affiliate_withdrawals",
        type_="check",
    )

    op.create_check_constraint(
        "ck_affiliate_withdrawal_status",
        "affiliate_withdrawals",
        """
        status IN (
            'PENDING',
            'APPROVED',
            'PROCESSING',
            'PAID',
            'FAILED',
            'REJECTED'
        )
        """,
    )

    # 2. Add payout provider and transaction tracking fields.
    op.add_column(
        "affiliate_withdrawals",
        sa.Column("provider", sa.String(length=30), nullable=True),
    )

    op.add_column(
        "affiliate_withdrawals",
        sa.Column(
            "provider_reference",
            sa.String(length=150),
            nullable=True,
        ),
    )

    # A provider reference must not identify multiple withdrawals.
    op.create_unique_constraint(
        "uq_affiliate_withdrawals_provider_reference",
        "affiliate_withdrawals",
        ["provider_reference"],
    )

    op.add_column(
        "affiliate_withdrawals",
        sa.Column(
            "beneficiary_reference",
            sa.String(length=150),
            nullable=True,
        ),
    )

    op.add_column(
        "affiliate_withdrawals",
        sa.Column(
            "payment_initiated_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    op.add_column(
        "affiliate_withdrawals",
        sa.Column(
            "failure_reason",
            sa.Text(),
            nullable=True,
        ),
    )

    op.add_column(
        "affiliate_withdrawals",
        sa.Column(
            "last_provider_status",
            sa.String(length=50),
            nullable=True,
        ),
    )


def downgrade() -> None:
    # Remove new payout tracking fields.
    op.drop_column(
        "affiliate_withdrawals",
        "last_provider_status",
    )

    op.drop_column(
        "affiliate_withdrawals",
        "failure_reason",
    )

    op.drop_column(
        "affiliate_withdrawals",
        "payment_initiated_at",
    )

    op.drop_column(
        "affiliate_withdrawals",
        "beneficiary_reference",
    )

    op.drop_constraint(
        "uq_affiliate_withdrawals_provider_reference",
        "affiliate_withdrawals",
        type_="unique",
    )

    op.drop_column(
        "affiliate_withdrawals",
        "provider_reference",
    )

    op.drop_column(
        "affiliate_withdrawals",
        "provider",
    )

    # Restore the original status constraint.
    # Downgrade will fail if PROCESSING or FAILED rows still exist.
    op.drop_constraint(
        "ck_affiliate_withdrawal_status",
        "affiliate_withdrawals",
        type_="check",
    )

    op.create_check_constraint(
        "ck_affiliate_withdrawal_status",
        "affiliate_withdrawals",
        """
        status IN (
            'PENDING',
            'APPROVED',
            'REJECTED',
            'PAID'
        )
        """,
    )