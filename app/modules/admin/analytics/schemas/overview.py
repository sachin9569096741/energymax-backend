from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class AnalyticsMetrics(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    orders: int
    order_value_total: Decimal
    gross_revenue: Decimal
    refunds: Decimal
    net_revenue: Decimal
    average_order_value: Decimal


class AnalyticsOverviewResponse(BaseModel):
    current: AnalyticsMetrics
    previous: AnalyticsMetrics


class AnalyticsDateRange(BaseModel):
    start_date: datetime
    end_date: datetime