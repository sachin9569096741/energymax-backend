"""add_affiliate_kyc_tables

Revision ID: 2a34b809f13f
Revises: 0e9d40dcb11f
Create Date: 2026-10-29 11:09:48.887867

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# Revision identifiers used by Alembic.
revision: str = "2a34b809f13f"
down_revision: Union[str, Sequence[str], None] = "0e9d40dcb11f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create Affiliate KYC tables."""

    # ---------------------------------------------------------
    # 1. Affiliate KYC submissions
    # ---------------------------------------------------------
    op.create_table(
        "affiliate_kyc_submissions",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "public_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "affiliate_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=30),
            nullable=False,
        ),
        sa.Column(
            "assigned_reviewer_id",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "submitted_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "reviewed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "decision_reason",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ("
            "'PENDING_REVIEW', "
            "'IN_REVIEW', "
            "'RESUBMISSION_REQUIRED', "
            "'REJECTED', "
            "'VERIFIED'"
            ")",
            name="ck_affiliate_kyc_submission_status",
        ),
        sa.ForeignKeyConstraint(
            ["affiliate_id"],
            ["affiliates.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["assigned_reviewer_id"],
            ["admin_users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_affiliate_kyc_submission_affiliate_created",
        "affiliate_kyc_submissions",
        ["affiliate_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_affiliate_kyc_submission_queue",
        "affiliate_kyc_submissions",
        ["status", "submitted_at"],
        unique=False,
    )
    op.create_index(
        "ix_affiliate_kyc_submission_reviewer_status",
        "affiliate_kyc_submissions",
        ["assigned_reviewer_id", "status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_affiliate_kyc_submissions_affiliate_id"),
        "affiliate_kyc_submissions",
        ["affiliate_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_affiliate_kyc_submissions_assigned_reviewer_id"),
        "affiliate_kyc_submissions",
        ["assigned_reviewer_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_affiliate_kyc_submissions_public_id"),
        "affiliate_kyc_submissions",
        ["public_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_affiliate_kyc_submissions_status"),
        "affiliate_kyc_submissions",
        ["status"],
        unique=False,
    )

    # ---------------------------------------------------------
    # 2. Affiliate KYC documents
    # ---------------------------------------------------------
    op.create_table(
        "affiliate_kyc_documents",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "public_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "submission_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "document_type",
            sa.String(length=30),
            nullable=False,
        ),
        sa.Column(
            "storage_key",
            sa.String(length=1024),
            nullable=False,
        ),
        sa.Column(
            "original_filename",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "content_type",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "file_size_bytes",
            sa.BigInteger(),
            nullable=False,
        ),
        sa.Column(
            "sha256_checksum",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.CheckConstraint(
            "document_type IN ("
            "'AADHAAR_FRONT', "
            "'AADHAAR_BACK', "
            "'PAN_CARD'"
            ")",
            name="ck_affiliate_kyc_document_type",
        ),
        sa.CheckConstraint(
            "file_size_bytes > 0",
            name="ck_affiliate_kyc_document_positive_size",
        ),
        sa.ForeignKeyConstraint(
            ["submission_id"],
            ["affiliate_kyc_submissions.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_key"),
        sa.UniqueConstraint(
            "submission_id",
            "document_type",
            name="uq_affiliate_kyc_submission_document_type",
        ),
    )

    op.create_index(
        "ix_affiliate_kyc_document_submission_type",
        "affiliate_kyc_documents",
        ["submission_id", "document_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_affiliate_kyc_documents_public_id"),
        "affiliate_kyc_documents",
        ["public_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_affiliate_kyc_documents_submission_id"),
        "affiliate_kyc_documents",
        ["submission_id"],
        unique=False,
    )

    # ---------------------------------------------------------
    # 3. Affiliate KYC review history
    # ---------------------------------------------------------
    op.create_table(
        "affiliate_kyc_review_history",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "public_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "submission_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "reviewer_id",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "previous_status",
            sa.String(length=30),
            nullable=True,
        ),
        sa.Column(
            "new_status",
            sa.String(length=30),
            nullable=False,
        ),
        sa.Column(
            "action",
            sa.String(length=40),
            nullable=False,
        ),
        sa.Column(
            "reason",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.CheckConstraint(
            "action IN ("
            "'CLAIMED', "
            "'APPROVED', "
            "'REJECTED', "
            "'RESUBMISSION_REQUESTED', "
            "'REASSIGNED'"
            ")",
            name="ck_affiliate_kyc_review_action",
        ),
        sa.CheckConstraint(
            "new_status IN ("
            "'PENDING_REVIEW', "
            "'IN_REVIEW', "
            "'RESUBMISSION_REQUIRED', "
            "'REJECTED', "
            "'VERIFIED'"
            ")",
            name="ck_affiliate_kyc_review_new_status",
        ),
        sa.CheckConstraint(
            "previous_status IS NULL OR previous_status IN ("
            "'PENDING_REVIEW', "
            "'IN_REVIEW', "
            "'RESUBMISSION_REQUIRED', "
            "'REJECTED', "
            "'VERIFIED'"
            ")",
            name="ck_affiliate_kyc_review_previous_status",
        ),
        sa.ForeignKeyConstraint(
            ["reviewer_id"],
            ["admin_users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["submission_id"],
            ["affiliate_kyc_submissions.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_affiliate_kyc_history_reviewer_created",
        "affiliate_kyc_review_history",
        ["reviewer_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_affiliate_kyc_history_submission_created",
        "affiliate_kyc_review_history",
        ["submission_id", "created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_affiliate_kyc_review_history_created_at"),
        "affiliate_kyc_review_history",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_affiliate_kyc_review_history_public_id"),
        "affiliate_kyc_review_history",
        ["public_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_affiliate_kyc_review_history_reviewer_id"),
        "affiliate_kyc_review_history",
        ["reviewer_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_affiliate_kyc_review_history_submission_id"),
        "affiliate_kyc_review_history",
        ["submission_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop Affiliate KYC tables."""

    # Drop dependent tables before their parent submission table.
    op.drop_index(
        op.f("ix_affiliate_kyc_review_history_submission_id"),
        table_name="affiliate_kyc_review_history",
    )
    op.drop_index(
        op.f("ix_affiliate_kyc_review_history_reviewer_id"),
        table_name="affiliate_kyc_review_history",
    )
    op.drop_index(
        op.f("ix_affiliate_kyc_review_history_public_id"),
        table_name="affiliate_kyc_review_history",
    )
    op.drop_index(
        op.f("ix_affiliate_kyc_review_history_created_at"),
        table_name="affiliate_kyc_review_history",
    )
    op.drop_index(
        "ix_affiliate_kyc_history_submission_created",
        table_name="affiliate_kyc_review_history",
    )
    op.drop_index(
        "ix_affiliate_kyc_history_reviewer_created",
        table_name="affiliate_kyc_review_history",
    )
    op.drop_table("affiliate_kyc_review_history")

    op.drop_index(
        op.f("ix_affiliate_kyc_documents_submission_id"),
        table_name="affiliate_kyc_documents",
    )
    op.drop_index(
        op.f("ix_affiliate_kyc_documents_public_id"),
        table_name="affiliate_kyc_documents",
    )
    op.drop_index(
        "ix_affiliate_kyc_document_submission_type",
        table_name="affiliate_kyc_documents",
    )
    op.drop_table("affiliate_kyc_documents")

    op.drop_index(
        op.f("ix_affiliate_kyc_submissions_status"),
        table_name="affiliate_kyc_submissions",
    )
    op.drop_index(
        op.f("ix_affiliate_kyc_submissions_public_id"),
        table_name="affiliate_kyc_submissions",
    )
    op.drop_index(
        op.f("ix_affiliate_kyc_submissions_assigned_reviewer_id"),
        table_name="affiliate_kyc_submissions",
    )
    op.drop_index(
        op.f("ix_affiliate_kyc_submissions_affiliate_id"),
        table_name="affiliate_kyc_submissions",
    )
    op.drop_index(
        "ix_affiliate_kyc_submission_reviewer_status",
        table_name="affiliate_kyc_submissions",
    )
    op.drop_index(
        "ix_affiliate_kyc_submission_queue",
        table_name="affiliate_kyc_submissions",
    )
    op.drop_index(
        "ix_affiliate_kyc_submission_affiliate_created",
        table_name="affiliate_kyc_submissions",
    )
    op.drop_table("affiliate_kyc_submissions")