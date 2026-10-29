from __future__ import annotations

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.affiliate.security.dependencies import (
    get_current_affiliate,
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
    ManualKYCStatusResponse,
    ManualKYCSubmissionResponse,
)


router = APIRouter(
    prefix="/affiliate/kyc/manual",
    tags=["Affiliate - Manual KYC"],
)


def get_kyc_storage():
    try:
        return LocalDevelopmentKYCStorage()
    except KYCStorageError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Private KYC storage is not configured.",
        ) from exc


def get_manual_kyc_service(
    db: Session = Depends(get_db),
) -> ManualKYCService:
    return ManualKYCService(db)


def map_kyc_exception(exc: ManualKYCError) -> HTTPException:
    if isinstance(exc, ManualKYCNotFoundError):
        return HTTPException(
            status_code=404,
            detail=str(exc),
        )

    if isinstance(exc, ManualKYCPermissionError):
        return HTTPException(
            status_code=403,
            detail=str(exc),
        )

    if isinstance(exc, ManualKYCValidationError):
        return HTTPException(
            status_code=422,
            detail=str(exc),
        )

    return HTTPException(
        status_code=400,
        detail=str(exc),
    )


@router.get(
    "/status",
    response_model=ManualKYCStatusResponse,
)
def get_manual_kyc_status(
    affiliate=Depends(get_current_affiliate),
    service: ManualKYCService = Depends(get_manual_kyc_service),
):
    try:
        return service.get_status(affiliate.id)
    except ManualKYCError as exc:
        raise map_kyc_exception(exc) from exc


@router.post(
    "/submit",
    response_model=ManualKYCSubmissionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_manual_kyc(
    aadhaar_front: UploadFile = File(...),
    aadhaar_back: UploadFile = File(...),
    pan_card: UploadFile = File(...),
    affiliate=Depends(get_current_affiliate),
    service: ManualKYCService = Depends(get_manual_kyc_service),
    storage=Depends(get_kyc_storage),
):
    uploads = [
        ("AADHAAR_FRONT", aadhaar_front),
        ("AADHAAR_BACK", aadhaar_back),
        ("PAN_CARD", pan_card),
    ]

    documents = []

    try:
        for document_type, upload in uploads:
            # Read at most 5 MB + 1 byte, so an oversized upload
            # is rejected without loading the entire file.
            data = await upload.read(5 * 1024 * 1024 + 1)

            if len(data) > 5 * 1024 * 1024:
                raise HTTPException(
                    status_code=413,
                    detail=f"{document_type} exceeds the 5 MB limit.",
                )

            documents.append(
                {
                    "document_type": document_type,
                    "filename": upload.filename or "",
                    "content_type": upload.content_type or "",
                    "data": data,
                }
            )

        submission = service.submit_documents(
            affiliate_id=affiliate.id,
            documents=documents,
            storage=storage,
        )

        # Never return storage_key.
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
            "review_history": [],
        }

    except ManualKYCError as exc:
        raise map_kyc_exception(exc) from exc

    finally:
        for _, upload in uploads:
            await upload.close()


@router.get("/documents")
def get_manual_kyc_documents(
    affiliate=Depends(get_current_affiliate),
    db=Depends(get_db),
):
    service = ManualKYCService(db)

    try:
        return service.get_documents(affiliate.id)
    except ManualKYCError as exc:
        raise map_kyc_exception(exc) from exc