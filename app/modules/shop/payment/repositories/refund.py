from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.shop.payment.models.payment_refund import PaymentRefund


class RefundRepository:

    def __init__(self, db: Session):
        self.db = db

    def get_by_public_id(
        self,
        public_id: str,
    ) -> PaymentRefund | None:
        statement = select(PaymentRefund).where(
            PaymentRefund.public_id == public_id
        )

        return self.db.scalar(statement)

    def get_by_idempotency_key(
        self,
        payment_id: int,
        idempotency_key: str,
    ) -> PaymentRefund | None:
        statement = select(PaymentRefund).where(
            PaymentRefund.payment_id == payment_id,
            PaymentRefund.idempotency_key == idempotency_key,
        )

        return self.db.scalar(statement)

    def get_by_provider_refund_id(
        self,
        provider_refund_id: str,
    ) -> PaymentRefund | None:
        statement = select(PaymentRefund).where(
            PaymentRefund.provider_refund_id == provider_refund_id
        )

        return self.db.scalar(statement)

    def get_by_payment_id(
        self,
        payment_id: int,
    ) -> list[PaymentRefund]:
        statement = (
            select(PaymentRefund)
            .where(PaymentRefund.payment_id == payment_id)
            .order_by(PaymentRefund.created_at.desc())
        )

        return list(self.db.scalars(statement).all())

    def get_total_refunded(
        self,
        payment_id: int,
    ) -> Decimal:
        statement = select(
            func.coalesce(
                func.sum(PaymentRefund.amount),
                0,
            )
        ).where(
            PaymentRefund.payment_id == payment_id,
            PaymentRefund.status.in_(
                [
                    "pending",
                    "succeeded",
                ]
            ),
        )

        result = self.db.scalar(statement)

        return Decimal(str(result or 0))


    def get_total_successful_refunded(self, payment_id: int) -> Decimal:
        statement = select(
            func.coalesce(
                func.sum(PaymentRefund.amount),
                0,
            )
        ).where(
            PaymentRefund.payment_id == payment_id,
            PaymentRefund.status == "succeeded",
        )

        result = self.db.scalar(statement)

        return Decimal(str(result or 0))

    def create(
        self,
        refund: PaymentRefund,
    ) -> PaymentRefund:
        self.db.add(refund)
        self.db.flush()

        return refund

    def save(
        self,
    ) -> None:
        self.db.flush()