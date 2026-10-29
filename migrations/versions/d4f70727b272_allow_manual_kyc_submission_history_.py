
"""allow manual KYC submission history actions

Revision ID: d4f70727b272
Revises: 2a34b809f13f
Create Date: 2026-10-29 11:42:45.038770
"""

from typing import Sequence, Union

from alembic import op


# Revision identifiers used by Alembic.
revision: str = "d4f70727b272"
down_revision: Union[str, Sequence[str], None] = "2a34b809f13f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_affiliate_kyc_review_action",
        "affiliate_kyc_review_history",
        type_="check",
    )

    op.create_check_constraint(
        "ck_affiliate_kyc_review_action",
        "affiliate_kyc_review_history",
        """
        action IN (
            'CLAIMED',
            'APPROVED',
            'REJECTED',
            'RESUBMISSION_REQUESTED',
            'REASSIGNED',
            'SUBMITTED',
            'RESUBMITTED'
        )
        """,
    )


def downgrade() -> None:
    # Remove history entries that the original constraint cannot support.
    op.execute(
        """
        DELETE FROM affiliate_kyc_review_history
        WHERE action IN ('SUBMITTED', 'RESUBMITTED')
        """
    )

    op.drop_constraint(
        "ck_affiliate_kyc_review_action",
        "affiliate_kyc_review_history",
        type_="check",
    )

    op.create_check_constraint(
        "ck_affiliate_kyc_review_action",
        "affiliate_kyc_review_history",
        """
        action IN (
            'CLAIMED',
            'APPROVED',
            'REJECTED',
            'RESUBMISSION_REQUESTED',
            'REASSIGNED'
        )
        """,
    )
