from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


KYCStatus = Literal[
    "NOT_STARTED",
    "PENDING_REVIEW",
    "IN_REVIEW",
    "RESUBMISSION_REQUIRED",
    "REJECTED",
    "VERIFIED",
]

DocumentType = Literal[
    "AADHAAR_FRONT",
    "AADHAAR_BACK",
    "PAN_CARD",
]

ReviewDecision = Literal[
    "APPROVED",
    "REJECTED",
    "RESUBMISSION_REQUESTED",
]


class ManualKYCStatusResponse(BaseModel):
    status: KYCStatus
    submission_id: str | None = None
    submitted_at: datetime | None = None
    reviewed_at: datetime | None = None
    decision_reason: str | None = None


class KYCDocumentResponse(BaseModel):
    public_id: str
    document_type: DocumentType
    original_filename: str
    content_type: str
    file_size_bytes: int
    sha256_checksum: str
    uploaded_at: datetime

    model_config = ConfigDict(from_attributes=True)


class KYCReviewHistoryResponse(BaseModel):
    public_id: str
    reviewer_id: int | None = None
    previous_status: str | None = None
    new_status: str
    action: str
    reason: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminKYCSubmissionResponse(BaseModel):
    public_id: str
    affiliate_id: int
    status: KYCStatus
    assigned_reviewer_id: int | None = None
    submitted_at: datetime
    reviewed_at: datetime | None = None
    decision_reason: str | None = None
    documents: list[KYCDocumentResponse] = Field(
        default_factory=list
    )
    review_history: list[KYCReviewHistoryResponse] = Field(
        default_factory=list
    )


class KYCDecisionRequest(BaseModel):
    decision: ReviewDecision
    reason: str | None = Field(
        default=None,
        max_length=2000,
    )


class KYCMessageResponse(BaseModel):
    message: str
    status: KYCStatus
    submission_id: str
    

class ManualKYCSubmissionResponse(BaseModel):
    public_id: str
    affiliate_id: int
    status: KYCStatus
    assigned_reviewer_id: int | None = None
    submitted_at: datetime
    reviewed_at: datetime | None = None
    decision_reason: str | None = None
    documents: list[KYCDocumentResponse] = Field(
        default_factory=list
    )
    review_history: list[KYCReviewHistoryResponse] = Field(
        default_factory=list
    )