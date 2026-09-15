from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.modules.shop.order.models.order import Order


class OrderRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_public_id(
        self,
        public_id: str,
        customer_id: int,
    ) -> Order | None:
        statement = (
            select(Order)
            .options(selectinload(Order.items))
            .where(
                Order.public_id == public_id,
                Order.customer_id == customer_id,
            )
        )

        return self.db.scalar(statement)

    def get_by_id(self, order_id: int):
        statement = (
            select(Order)
            .where(Order.id == order_id)
        )
        return self.db.scalar(statement)
    def get_by_checkout_id(
        self,
        checkout_id: int,
    ) -> Order | None:
        statement = (
            select(Order)
            .options(selectinload(Order.items))
            .where(Order.checkout_id == checkout_id)
        )

        return self.db.scalar(statement)

    def create(self, order: Order) -> Order:
        self.db.add(order)
        self.db.flush()
        return order

    def save(self) -> None:
        self.db.flush()