from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import func, select
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
            .options(
                selectinload(Order.items),
                selectinload(Order.status_history),
            )
            .where(
                Order.public_id == public_id,
                Order.customer_id == customer_id,
            )
        )

        return self.db.scalar(statement)

    def get_admin_by_public_id(
        self,
        public_id: str,
    ) -> Order | None:
        statement = (
            select(Order)
            .options(
                selectinload(Order.items),
                selectinload(Order.status_history),
            )
            .where(
                Order.public_id == public_id,
            )
        )

        return self.db.scalar(statement)

    def get_by_id(
        self,
        order_id: int,
    ) -> Order | None:
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
            .options(
                selectinload(Order.items),
                selectinload(Order.status_history),
            )
            .where(
                Order.checkout_id == checkout_id,
            )
        )

        return self.db.scalar(statement)
    def list_admin_orders(
        self,
        *,
        page: int,
        page_size: int,
        status: str | None = None,
        search: str | None = None,
    ):
        offset = (page - 1) * page_size

        conditions = []

        if status:
            conditions.append(Order.status == status)

        if search:
            search_value = f"%{search.strip()}%"

            conditions.append(
                (
                    Order.order_number.ilike(search_value)
                    | Order.customer_name.ilike(search_value)
                    | Order.customer_email.ilike(search_value)
                    | Order.customer_phone.ilike(search_value)
                )
            )

        count_statement = select(
            func.count(Order.id)
        ).where(*conditions)

        total = self.db.scalar(count_statement) or 0

        statement = (
            select(Order)
            .where(*conditions)
            .order_by(Order.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )

        orders = list(self.db.scalars(statement).all())

        return orders, total

    def get_by_order_number_for_tracking(
        self,
        order_number: str,
    ) -> Order | None:
        statement = (
            select(Order)
            .options(
                selectinload(Order.status_history),
            )
            .where(
                Order.order_number == order_number,
            )
        )

        return self.db.scalar(statement)
    def create(
        self,
        order: Order,
    ) -> Order:
        self.db.add(order)
        self.db.flush()

        return order

    def save(self) -> None:
        self.db.flush()