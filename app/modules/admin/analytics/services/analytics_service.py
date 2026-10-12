from datetime import date, datetime, time, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.modules.admin.analytics.repositories.repository import (
    AnalyticsRepository,
)


class AnalyticsService:
    def __init__(self, db: Session):
        self.repository = AnalyticsRepository(db)

    def get_overview(
        self,
        start_date: date,
        end_date: date,
    ) -> dict:
        if start_date > end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="start_date must be on or before end_date.",
            )

        # Treat the supplied dates as UTC calendar dates.
        current_start = datetime.combine(
            start_date,
            time.min,
            tzinfo=timezone.utc,
        )
        current_end = datetime.combine(
            end_date + timedelta(days=1),
            time.min,
            tzinfo=timezone.utc,
        )

        period_length = (end_date - start_date).days + 1
        previous_end = current_start
        previous_start = previous_end - timedelta(days=period_length)

        return self.repository.get_overview(
            start_date=current_start,
            end_date=current_end,
            previous_start_date=previous_start,
            previous_end_date=previous_end,
        )