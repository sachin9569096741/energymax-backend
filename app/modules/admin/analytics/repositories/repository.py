from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.shop.order.models.order import Order
from app.modules.shop.payment.models.payment import Payment
from app.modules.shop.payment.models.payment_refund import PaymentRefund


class AnalyticsRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_overview(
        self,
        start_date: datetime,
        end_date: datetime,
        previous_start_date: datetime,
        previous_end_date: datetime,
    ) -> dict:
        current = self._get_period_metrics(start_date, end_date)
        previous = self._get_period_metrics(
            previous_start_date,
            previous_end_date,
        )

        return {
            "current": current,
            "previous": previous,
        }

    def _get_period_metrics(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> dict:
        successful_payments = (
            select(
                func.coalesce(
                    func.sum(Payment.amount),
                    0,
                )
            )
            .where(
                Payment.created_at >= start_date,
                Payment.created_at < end_date,
                func.lower(Payment.status).in_(
                    ["success", "succeeded", "captured", "paid"]
                ),
            )
        )

        successful_refunds = (
            select(
                func.coalesce(
                    func.sum(PaymentRefund.amount),
                    0,
                )
            )
            .where(
                PaymentRefund.created_at >= start_date,
                PaymentRefund.created_at < end_date,
                func.lower(PaymentRefund.status).in_(
                    ["success", "succeeded", "processed", "completed"]
                ),
            )
        )

        order_metrics = (
            self.db.query(
                func.count(Order.id),
                func.coalesce(
                    func.sum(Order.total_amount),
                    0,
                ),
            )
            .filter(
                Order.created_at >= start_date,
                Order.created_at < end_date,
            )
            .one()
        )

        gross_revenue = Decimal(
            str(self.db.execute(successful_payments).scalar_one())
        )

        refund_total = Decimal(
            str(self.db.execute(successful_refunds).scalar_one())
        )

        order_count = int(order_metrics[0] or 0)
        order_value_total = Decimal(str(order_metrics[1] or 0))

        return {
            "orders": order_count,
            "order_value_total": order_value_total,
            "gross_revenue": gross_revenue,
            "refunds": refund_total,
            "net_revenue": gross_revenue - refund_total,
            "average_order_value": (
                order_value_total / order_count
                if order_count
                else Decimal("0.00")
            ),
        }