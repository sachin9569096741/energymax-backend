from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.admin.auth.models.admin_user import AdminUser
from app.modules.admin.auth.security.dependencies import require_super_admin
from app.modules.affiliate.schemas.commission import (
    CommissionPolicyCreate,
    CommissionPolicyResponse,
)
from app.modules.affiliate.services.commission_policy_service import (
    CommissionPolicyService,
)


router = APIRouter(
    prefix="/admin/affiliates/commission-policies",
    tags=["Admin - Affiliate Commissions"],
)


@router.post(
    "",
    response_model=CommissionPolicyResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_commission_policy(
    payload: CommissionPolicyCreate,
    admin: AdminUser = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    service = CommissionPolicyService(db)

    try:
        policy = service.create_policy(
            payload=payload,
            admin_id=admin.id,
        )
        db.commit()
        db.refresh(policy)
        return policy
    except Exception:
        db.rollback()
        raise


@router.get(
    "",
    response_model=list[CommissionPolicyResponse],
)
def list_commission_policies(
    affiliate_public_id: str | None = Query(default=None),
    active_only: bool = Query(default=False),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _admin: AdminUser = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    return CommissionPolicyService(db).list_policies(
        affiliate_public_id=affiliate_public_id,
        active_only=active_only,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/{public_id}/deactivate",
    response_model=CommissionPolicyResponse,
)
def deactivate_commission_policy(
    public_id: str,
    _admin: AdminUser = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    service = CommissionPolicyService(db)

    try:
        policy = service.deactivate_policy(public_id)
        db.commit()
        db.refresh(policy)
        return policy
    except Exception:
        db.rollback()
        raise