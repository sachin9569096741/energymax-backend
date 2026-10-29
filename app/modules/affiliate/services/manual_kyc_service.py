
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.modules.affiliate.models.affiliate import Affiliate
from app.modules.affiliate.models.affiliate_kyc_submission import (
    AffiliateKYCSubmission,
)
from app.modules.affiliate.models.affiliate_kyc_document import (
    AffiliateKYCDocument,
)
from app.modules.affiliate.models.affiliate_kyc_review_history import (
    AffiliateKYCReviewHistory,
)
from app.modules.admin.auth.models.admin_user import AdminUser

from app.modules.affiliate.services.kyc_storage import (
    ALLOWED_CONTENT_TYPES,
    ALLOWED_DOCUMENTS,
    MAX_KYC_FILE_SIZE,
    KYCStorageError,
    calculate_sha256,
    detect_file_type,
)


KYC_STATUSES = {
    "PENDING_REVIEW",
    "IN_REVIEW",
    "RESUBMISSION_REQUIRED",
    "REJECTED",
    "VERIFIED",
}

REQUIRED_DOCUMENTS = {
    "AADHAAR_FRONT",
    "AADHAAR_BACK",
    "PAN_CARD",
}

MAX_FILENAME_LENGTH = 255


class ManualKYCError(Exception):
    """Base exception for manual KYC business logic."""


class ManualKYCNotFoundError(ManualKYCError):
    pass


class ManualKYCValidationError(ManualKYCError):
    pass


class ManualKYCPermissionError(ManualKYCError):
    pass


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ManualKYCService:
    """
    Manual affiliate KYC workflow.

    This service never automatically verifies documents.
    Verification requires an explicit reviewer decision.
    """

    def __init__(self, db: Session):
        self.db = db

    # ---------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------

    def _get_affiliate(self, affiliate_id: int) -> Affiliate:
        affiliate = self.db.scalar(
            select(Affiliate).where(Affiliate.id == affiliate_id)
        )

        if affiliate is None:
            raise ManualKYCNotFoundError("Affiliate not found.")

        if str(affiliate.status).lower() != "active":
            raise ManualKYCPermissionError(
                "Your affiliate account is not active."
            )

        return affiliate

    def _get_submission(
        self,
        submission_id: int,
        *,
        lock: bool = False,
    ) -> AffiliateKYCSubmission:
        statement = (
            select(AffiliateKYCSubmission)
            .options(
                selectinload(AffiliateKYCSubmission.documents),
                selectinload(AffiliateKYCSubmission.review_history),
            )
            .where(AffiliateKYCSubmission.id == submission_id)
        )

        if lock:
            statement = statement.with_for_update()

        submission = self.db.scalar(statement)

        if submission is None:
            raise ManualKYCNotFoundError(
                "KYC submission not found."
            )

        return submission

    def _add_history(
        self,
        *,
        submission: AffiliateKYCSubmission,
        reviewer_id: int | None,
        previous_status: str | None,
        new_status: str,
        action: str,
        reason: str | None = None,
    ) -> None:
        self.db.add(
            AffiliateKYCReviewHistory(
                submission_id=submission.id,
                reviewer_id=reviewer_id,
                previous_status=previous_status,
                new_status=new_status,
                action=action,
                reason=reason,
            )
        )

    @staticmethod
    def _validate_document(
        *,
        document_type: str,
        filename: str,
        declared_content_type: str,
        data: bytes,
    ) -> tuple[str, str]:
        if document_type not in ALLOWED_DOCUMENTS:
            raise ManualKYCValidationError(
                f"Unsupported document type: {document_type}."
            )

        if not filename or not filename.strip():
            raise ManualKYCValidationError(
                "A filename is required."
            )

        filename = filename.replace("\\", "/").split("/")[-1].strip()

        if not filename or filename in {".", ".."}:
            raise ManualKYCValidationError(
                "Invalid filename."
            )

        if len(filename) > MAX_FILENAME_LENGTH:
            raise ManualKYCValidationError(
                "Filename must not exceed 255 characters."
            )

        if not data:
            raise ManualKYCValidationError(
                f"{document_type} file is empty."
            )

        if len(data) > MAX_KYC_FILE_SIZE:
            raise ManualKYCValidationError(
                f"{document_type} exceeds the 5 MB file limit."
            )

        try:
            detected_type = detect_file_type(data)
        except KYCStorageError as exc:
            raise ManualKYCValidationError(str(exc)) from exc

        declared_content_type = (
            declared_content_type or ""
        ).split(";")[0].strip().lower()

        if detected_type not in ALLOWED_CONTENT_TYPES:
            raise ManualKYCValidationError(
                "Unsupported document format."
            )

        if declared_content_type != detected_type:
            raise ManualKYCValidationError(
                "File content does not match its declared content type."
            )

        return filename, detected_type

    # ---------------------------------------------------------
    # Affiliate: get current status
    # ---------------------------------------------------------

    def get_status(self, affiliate_id: int) -> dict:
        self._get_affiliate(affiliate_id)

        submission = self.db.scalar(
            select(AffiliateKYCSubmission)
            .where(
                AffiliateKYCSubmission.affiliate_id == affiliate_id
            )
            .order_by(
                AffiliateKYCSubmission.created_at.desc(),
                AffiliateKYCSubmission.id.desc(),
            )
        )

        if submission is None:
            return {
                "status": "NOT_STARTED",
                "submission_id": None,
                "submitted_at": None,
                "reviewed_at": None,
                "decision_reason": None,
            }

        return {
            "status": submission.status,
            "submission_id": submission.public_id,
            "submitted_at": submission.submitted_at,
            "reviewed_at": submission.reviewed_at,
            "decision_reason": submission.decision_reason,
        }

    # ---------------------------------------------------------
    # Affiliate: submit all required documents
    # ---------------------------------------------------------

    def submit_documents(
        self,
        *,
        affiliate_id: int,
        documents: list[dict],
        storage,
    ) -> AffiliateKYCSubmission:
        """
        Submit all three documents together.

        Expected document item:
        {
            "document_type": "PAN_CARD",
            "filename": "pan.pdf",
            "content_type": "application/pdf",
            "data": b"..."
        }

        The supplied affiliate_id must come from the authenticated
        affiliate object in the route, never from the request body.
        """

        self._get_affiliate(affiliate_id)

        if len(documents) != len(REQUIRED_DOCUMENTS):
            raise ManualKYCValidationError(
                "Exactly three documents are required: "
                "Aadhaar front, Aadhaar back, and PAN card."
            )

        document_types = [
            item.get("document_type")
            for item in documents
        ]

        if (
            len(set(document_types)) != len(document_types)
            or set(document_types) != REQUIRED_DOCUMENTS
        ):
            raise ManualKYCValidationError(
                "Upload exactly one file for each required document type."
            )

        validated_documents = []

        # Validate every file before writing any files to storage.
        for item in documents:
            filename, detected_type = self._validate_document(
                document_type=item["document_type"],
                filename=item["filename"],
                declared_content_type=item["content_type"],
                data=item["data"],
            )

            validated_documents.append(
                {
                    "document_type": item["document_type"],
                    "filename": filename,
                    "content_type": detected_type,
                    "data": item["data"],
                    "checksum": calculate_sha256(item["data"]),
                }
            )

        latest_submission = self.db.scalar(
            select(AffiliateKYCSubmission)
            .where(
                AffiliateKYCSubmission.affiliate_id == affiliate_id
            )
            .order_by(
                AffiliateKYCSubmission.created_at.desc(),
                AffiliateKYCSubmission.id.desc(),
            )
            .with_for_update()
        )

        if latest_submission is not None:
            if latest_submission.status == "VERIFIED":
                raise ManualKYCValidationError(
                    "Your KYC is already verified."
                )

            if latest_submission.status in {
                "PENDING_REVIEW",
                "IN_REVIEW",
            }:
                raise ManualKYCValidationError(
                    "Your KYC is already awaiting review."
                )

            if latest_submission.status not in {
                "RESUBMISSION_REQUIRED",
                "REJECTED",
            }:
                raise ManualKYCValidationError(
                    "The current KYC submission cannot be resubmitted."
                )

        saved_storage_keys: list[str] = []

        try:
            # Store documents privately before committing their metadata.
            stored_documents = []

            for item in validated_documents:
                storage_key = storage.save(item["data"])
                saved_storage_keys.append(storage_key)

                stored_documents.append(
                    {
                        **item,
                        "storage_key": storage_key,
                    }
                )

            if latest_submission is None:
                submission = AffiliateKYCSubmission(
                    affiliate_id=affiliate_id,
                    status="PENDING_REVIEW",
                    submitted_at=utc_now(),
                )
                self.db.add(submission)
                self.db.flush()

                previous_status = None
                action = "SUBMITTED"

            else:
                submission = latest_submission
                previous_status = submission.status

                # This is a new review round. The previous submission
                # remains untouched, preserving its documents and history.
                submission = AffiliateKYCSubmission(
                    affiliate_id=affiliate_id,
                    status="PENDING_REVIEW",
                    submitted_at=utc_now(),
                )
                self.db.add(submission)
                self.db.flush()

                action = "RESUBMITTED"

            for item in stored_documents:
                self.db.add(
                    AffiliateKYCDocument(
                        submission_id=submission.id,
                        document_type=item["document_type"],
                        storage_key=item["storage_key"],
                        original_filename=item["filename"],
                        content_type=item["content_type"],
                        file_size_bytes=len(item["data"]),
                        sha256_checksum=item["checksum"],
                    )
                )

            self._add_history(
                submission=submission,
                reviewer_id=None,
                previous_status=previous_status,
                new_status="PENDING_REVIEW",
                action=action,
                reason=(
                    "Affiliate submitted the required KYC documents."
                ),
            )

            self.db.commit()

            return self._get_submission(submission.id)

        except Exception:
            self.db.rollback()

            # Best-effort cleanup if database persistence fails.
            for storage_key in saved_storage_keys:
                try:
                    storage.delete(storage_key)
                except Exception:
                    # Do not mask the original error.
                    pass

            raise

    # ---------------------------------------------------------
    # Admin: list submissions
    # ---------------------------------------------------------


    def get_documents(self, affiliate_id: int) -> dict:
        self._get_affiliate(affiliate_id)

        submission = self.db.scalar(
            select(AffiliateKYCSubmission)
            .where(
                AffiliateKYCSubmission.affiliate_id == affiliate_id
            )
            .order_by(
                AffiliateKYCSubmission.created_at.desc(),
                AffiliateKYCSubmission.id.desc(),
            )
        )

        if submission is None:
            return {
                "status": "NOT_STARTED",
                "submission_id": None,
                "documents": [],
            }

        documents = self.db.scalars(
            select(AffiliateKYCDocument)
            .where(
                AffiliateKYCDocument.submission_id == submission.id
            )
            .order_by(AffiliateKYCDocument.document_type)
        ).all()

        return {
            "status": submission.status,
            "submission_id": submission.public_id,
            "documents": [
                {
                    "document_type": document.document_type,
                    "uploaded": True,
                    "original_filename": document.original_filename,
                    "content_type": document.content_type,
                    "file_size_bytes": document.file_size_bytes,
                    "uploaded_at": document.uploaded_at,
                }
                for document in documents
            ],
        }
    def list_submissions(
        self,
        *,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AffiliateKYCSubmission]:
        if status is not None and status not in KYC_STATUSES:
            raise ManualKYCValidationError(
                "Invalid KYC status filter."
            )

        limit = max(1, min(limit, 100))
        offset = max(0, offset)

        statement = (
            select(AffiliateKYCSubmission)
            .options(
                selectinload(AffiliateKYCSubmission.documents),
            )
            .order_by(
                AffiliateKYCSubmission.submitted_at.asc(),
                AffiliateKYCSubmission.id.asc(),
            )
            .limit(limit)
            .offset(offset)
        )

        if status is not None:
            statement = statement.where(
                AffiliateKYCSubmission.status == status
            )

        return list(self.db.scalars(statement).all())

    # ---------------------------------------------------------
    # Admin: get submission and review history
    # ---------------------------------------------------------

    def get_submission(
        self,
        submission_id: int,
    ) -> AffiliateKYCSubmission:
        return self._get_submission(submission_id)

    # ---------------------------------------------------------
    # Admin: claim submission
    # ---------------------------------------------------------

    def claim_submission(
        self,
        *,
        submission_id: int,
        reviewer_id: int,
    ) -> AffiliateKYCSubmission:
        submission = self._get_submission(
            submission_id,
            lock=True,
        )

        reviewer = self.db.get(AdminUser, reviewer_id)

        if reviewer is None:
            raise ManualKYCNotFoundError(
                "Admin reviewer not found."
            )

        if submission.status != "PENDING_REVIEW":
            raise ManualKYCValidationError(
                "Only pending submissions can be claimed."
            )

        previous_status = submission.status

        submission.status = "IN_REVIEW"
        submission.assigned_reviewer_id = reviewer_id

        self._add_history(
            submission=submission,
            reviewer_id=reviewer_id,
            previous_status=previous_status,
            new_status="IN_REVIEW",
            action="CLAIMED",
            reason="Reviewer claimed the KYC submission.",
        )

        self.db.commit()

        return self._get_submission(submission.id)

    # ---------------------------------------------------------
    # Admin: review decision
    # ---------------------------------------------------------

    def decide_submission(
        self,
        *,
        submission_id: int,
        reviewer_id: int,
        decision: str,
        reason: str | None = None,
    ) -> AffiliateKYCSubmission:
        decision = decision.strip().upper()

        allowed_decisions = {
            "APPROVED",
            "REJECTED",
            "RESUBMISSION_REQUESTED",
        }

        if decision not in allowed_decisions:
            raise ManualKYCValidationError(
                "Decision must be APPROVED, REJECTED, "
                "or RESUBMISSION_REQUESTED."
            )

        if decision != "APPROVED" and not (
            reason and reason.strip()
        ):
            raise ManualKYCValidationError(
                "A reason is required for rejection or resubmission."
            )

        submission = self._get_submission(
            submission_id,
            lock=True,
        )

        reviewer = self.db.get(AdminUser, reviewer_id)

        if reviewer is None:
            raise ManualKYCNotFoundError(
                "Admin reviewer not found."
            )

        if submission.status != "IN_REVIEW":
            raise ManualKYCValidationError(
                "Only submissions currently in review can receive a decision."
            )

        if submission.assigned_reviewer_id != reviewer_id:
            raise ManualKYCPermissionError(
                "This submission is assigned to another reviewer."
            )

        if decision == "APPROVED":
            new_status = "VERIFIED"
            action = "APPROVED"

        elif decision == "REJECTED":
            new_status = "REJECTED"
            action = "REJECTED"

        else:
            new_status = "RESUBMISSION_REQUIRED"
            action = "RESUBMISSION_REQUESTED"

        previous_status = submission.status

        submission.status = new_status
        submission.reviewed_at = utc_now()
        submission.decision_reason = (
            reason.strip() if reason else None
        )

        self._add_history(
            submission=submission,
            reviewer_id=reviewer_id,
            previous_status=previous_status,
            new_status=new_status,
            action=action,
            reason=reason.strip() if reason else None,
        )

        self.db.commit()

        return self._get_submission(submission.id)

    # ---------------------------------------------------------
    # Admin: retrieve document bytes
    # ---------------------------------------------------------

    def get_document_bytes(
        self,
        *,
        submission_id: int,
        document_type: str,
        storage,
    ) -> tuple[bytes, str, str]:
        if document_type not in REQUIRED_DOCUMENTS:
            raise ManualKYCValidationError(
                "Invalid document type."
            )

        submission = self._get_submission(submission_id)

        document = next(
            (
                item
                for item in submission.documents
                if item.document_type == document_type
            ),
            None,
        )

        if document is None:
            raise ManualKYCNotFoundError(
                "Requested document was not found."
            )

        try:
            data = storage.read(document.storage_key)
        except KYCStorageError as exc:
            raise ManualKYCError(
                "Unable to retrieve the private document."
            ) from exc

        # Verify integrity before serving the stored document.
        if calculate_sha256(data) != document.sha256_checksum:
            raise ManualKYCError(
                "Stored document integrity verification failed."
            )

        return (
            data,
            document.content_type,
            document.original_filename,
        )
