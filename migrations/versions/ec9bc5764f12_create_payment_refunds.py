"""create payment refunds

Revision ID: ec9bc5764f12
Revises: 803599480718
Create Date: 2026-09-14 11:55:52.371783

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "ec9bc5764f12"
down_revision: Union[str, Sequence[str], None] = "803599480718"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "payment_refunds",

        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "public_id",
            sa.String(length=36),
            nullable=False,
        ),

        sa.Column(
            "payment_id",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "amount",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
        ),

        sa.Column(
            "currency",
            sa.String(length=3),
            nullable=False,
        ),

        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
        ),

        sa.Column(
            "provider",
            sa.String(length=32),
            nullable=False,
        ),

        sa.Column(
            "provider_refund_id",
            sa.String(length=128),
            nullable=True,
        ),

        sa.Column(
            "idempotency_key",
            sa.String(length=128),
            nullable=False,
        ),

        sa.Column(
            "reason",
            sa.Text(),
            nullable=True,
        ),

        sa.Column(
            "failure_code",
            sa.String(length=128),
            nullable=True,
        ),

        sa.Column(
            "failure_message",
            sa.Text(),
            nullable=True,
        ),

        sa.Column(
            "provider_response",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),

        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),

        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),

        sa.ForeignKeyConstraint(
            ["payment_id"],
            ["payments.id"],
            ondelete="CASCADE",
        ),

        sa.PrimaryKeyConstraint("id"),

        sa.UniqueConstraint(
            "public_id",
            name="uq_payment_refunds_public_id",
        ),

        sa.UniqueConstraint(
            "payment_id",
            "idempotency_key",
            name="uq_payment_refund_idempotency",
        ),
    )

    op.create_index(
        "ix_payment_refunds_public_id",
        "payment_refunds",
        ["public_id"],
        unique=True,
    )

    op.create_index(
        "ix_payment_refunds_payment_id",
        "payment_refunds",
        ["payment_id"],
        unique=False,
    )

    op.create_index(
        "ix_payment_refunds_status",
        "payment_refunds",
        ["status"],
        unique=False,
    )

    op.create_index(
        "ix_payment_refunds_provider_refund_id",
        "payment_refunds",
        ["provider_refund_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_payment_refunds_provider_refund_id",
        table_name="payment_refunds",
    )

    op.drop_index(
        "ix_payment_refunds_status",
        table_name="payment_refunds",
    )

    op.drop_index(
        "ix_payment_refunds_payment_id",
        table_name="payment_refunds",
    )

    op.drop_index(
        "ix_payment_refunds_public_id",
        table_name="payment_refunds",
    )

    op.drop_table("payment_refunds")