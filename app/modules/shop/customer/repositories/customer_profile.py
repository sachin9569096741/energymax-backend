from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.shop.customer.models.customer import Customer


class CustomerProfileRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_customer_by_email(
        self,
        email: str,
        exclude_customer_id: int | None = None,
    ) -> Customer | None:

        statement = select(Customer).where(
            Customer.email == email,
        )

        if exclude_customer_id is not None:
            statement = statement.where(
                Customer.id != exclude_customer_id,
            )

        return self.db.scalar(statement)

    def get_customer_by_phone(
        self,
        phone: str,
        exclude_customer_id: int | None = None,
    ) -> Customer | None:

        statement = select(Customer).where(
            Customer.phone == phone,
        )

        if exclude_customer_id is not None:
            statement = statement.where(
                Customer.id != exclude_customer_id,
            )

        return self.db.scalar(statement)

    def save(self, customer: Customer) -> Customer:
        self.db.add(customer)
        self.db.flush()

        return customer