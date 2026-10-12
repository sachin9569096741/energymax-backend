from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.admin.auth.models.admin_user import AdminUser
from app.modules.admin.auth.security.dependencies import require_permission
from app.modules.admin.analytics.schemas.overview import (
    AnalyticsOverviewResponse,
)
from app.modules.admin.analytics.services.analytics_service import (
    AnalyticsService,
)

router = APIRouter(
    prefix="/admin/analytics",
    tags=["Admin - Analytics"],
)


@router.get(
    "/overview",
    response_model=AnalyticsOverviewResponse,
)
def get_analytics_overview(
    start_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: date = Query(..., description="Inclusive end date (YYYY-MM-DD)"),
    current_admin: AdminUser = Depends(
        require_permission("analytics.view")
    ),
    db: Session = Depends(get_db),
):
    service = AnalyticsService(db)

    return service.get_overview(
        start_date=start_date,
        end_date=end_date,
    )