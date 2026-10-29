from __future__ import annotations

from urllib.parse import quote

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Response,
)
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.admin.auth.security.dependencies import (
    get_current_admin,
    require_permission,
)
from app.modules.affiliate.services.manual_kyc_service import (
    ManualKYCError,
    ManualKYCNotFoundError,
    ManualKYCPermissionError,
    ManualKYCService,
    ManualKYCValidationError,
)
from app.modules.affiliate.services.kyc_storage import (
    KYCStorageError,
    LocalDevelopmentKYCStorage,
)
from app.modules.affiliate.schemas.manual_kyc import (
    AdminKYCSubmissionResponse,
    KYCDecisionRequest,
)


router = APIRouter(
    prefix="/admin/affiliate-kyc",
    tags=["Admin - Affiliate KYC"],
)

review_permission = require_permission("affiliate.kyc.review")


def get_manual_kyc_service(
    db: Session = Depends(get_db),
) -> ManualKYCService:
    return ManualKYCService(db)


def get_kyc_storage():
    try:
        return LocalDevelopmentKYCStorage()
    except KYCStorageError as exc:
        raise HTTPException(
            status_code=503,
            detail="Private KYC storage is not configured.",
        ) from exc


def map_kyc_exception(exc: ManualKYCError) -> HTTPException:
    if isinstance(exc, ManualKYCNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))

    if isinstance(exc, ManualKYCPermissionError):
        return HTTPException(status_code=403, detail=str(exc))

    if isinstance(exc, ManualKYCValidationError):
        return HTTPException(status_code=422, detail=str(exc))

    return HTTPException(status_code=400, detail=str(exc))


def serialize_submission(submission):
    return {
        "public_id": submission.public_id,
        "affiliate_id": submission.affiliate_id,
        "status": submission.status,
        "assigned_reviewer_id": submission.assigned_reviewer_id,
        "submitted_at": submission.submitted_at,
        "reviewed_at": submission.reviewed_at,
        "decision_reason": submission.decision_reason,
        "documents": [
            {
                "public_id": document.public_id,
                "document_type": document.document_type,
                "original_filename": document.original_filename,
                "content_type": document.content_type,
                "file_size_bytes": document.file_size_bytes,
                "sha256_checksum": document.sha256_checksum,
                "uploaded_at": document.uploaded_at,
            }
            for document in submission.documents
        ],
        "review_history": [
            {
                "public_id": history.public_id,
                "reviewer_id": history.reviewer_id,
                "previous_status": history.previous_status,
                "new_status": history.new_status,
                "action": history.action,
                "reason": history.reason,
                "created_at": history.created_at,
            }
            for history in submission.review_history
        ],
    }


@router.get("")
def list_kyc_submissions(
    status_filter: str | None = Query(
        default=None,
        alias="status",
    ),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    admin=Depends(get_current_admin),
    _: None = Depends(review_permission),
    service: ManualKYCService = Depends(get_manual_kyc_service),
):
    try:
        submissions = service.list_submissions(
            status=status_filter,
            limit=limit,
            offset=offset,
        )

        return {
            "items": [
                serialize_submission(submission)
                for submission in submissions
            ],
            "limit": limit,
            "offset": offset,
        }

    except ManualKYCError as exc:
        raise map_kyc_exception(exc) from exc


@router.get(
    "/{submission_id}",
    response_model=AdminKYCSubmissionResponse,
)
def get_kyc_submission(
    submission_id: int,
    admin=Depends(get_current_admin),
    _: None = Depends(review_permission),
    service: ManualKYCService = Depends(get_manual_kyc_service),
):
    try:
        submission = service.get_submission(submission_id)
        return serialize_submission(submission)

    except ManualKYCError as exc:
        raise map_kyc_exception(exc) from exc


@router.post(
    "/{submission_id}/claim",
    response_model=AdminKYCSubmissionResponse,
)
def claim_kyc_submission(
    submission_id: int,
    admin=Depends(get_current_admin),
    _: None = Depends(review_permission),
    service: ManualKYCService = Depends(get_manual_kyc_service),
):
    try:
        submission = service.claim_submission(
            submission_id=submission_id,
            reviewer_id=admin.id,
        )
        return serialize_submission(submission)

    except ManualKYCError as exc:
        raise map_kyc_exception(exc) from exc


@router.post(
    "/{submission_id}/decision",
    response_model=AdminKYCSubmissionResponse,
)
def decide_kyc_submission(
    submission_id: int,
    payload: KYCDecisionRequest,
    admin=Depends(get_current_admin),
    _: None = Depends(review_permission),
    service: ManualKYCService = Depends(get_manual_kyc_service),
):
    try:
        submission = service.decide_submission(
            submission_id=submission_id,
            reviewer_id=admin.id,
            decision=payload.decision,
            reason=payload.reason,
        )
        return serialize_submission(submission)

    except ManualKYCError as exc:
        raise map_kyc_exception(exc) from exc


@router.get(
    "/{submission_id}/documents/{document_type}",
)
def download_kyc_document(
    submission_id: int,
    document_type: str,
    admin=Depends(get_current_admin),
    _: None = Depends(review_permission),
    service: ManualKYCService = Depends(get_manual_kyc_service),
    storage=Depends(get_kyc_storage),
):
    try:
        data, content_type, filename = service.get_document_bytes(
            submission_id=submission_id,
            document_type=document_type,
            storage=storage,
        )

        # Do not expose a permanent URL or internal storage key.
        safe_filename = quote(filename, safe="")

        return Response(
            content=data,
            media_type=content_type,
            headers={
                "Content-Disposition": (
                    f"inline; filename*=UTF-8''{safe_filename}"
                ),
                "Cache-Control": "no-store, private",
                "X-Content-Type-Options": "nosniff",
            },
        )

    except ManualKYCError as exc:
        raise map_kyc_exception(exc) from exc