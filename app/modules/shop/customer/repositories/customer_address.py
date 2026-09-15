from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.modules.shop.customer.models.customer_address import CustomerAddress


class CustomerAddressRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_public_id(
        self,
        public_id: str,
        customer_id: int,
    ) -> CustomerAddress | None:
        statement = select(CustomerAddress).where(
            CustomerAddress.public_id == public_id,
            CustomerAddress.customer_id == customer_id,
            CustomerAddress.is_active.is_(True),
        )

        return self.db.scalar(statement)

    def get_customer_addresses(
        self,
        customer_id: int,
    ) -> list[CustomerAddress]:
        statement = (
            select(CustomerAddress)
            .where(
                CustomerAddress.customer_id == customer_id,
                CustomerAddress.is_active.is_(True),
            )
            .order_by(
                CustomerAddress.is_default.desc(),
                CustomerAddress.created_at.desc(),
            )
        )

        return list(self.db.scalars(statement).all())

    def get_default_address(
        self,
        customer_id: int,
    ) -> CustomerAddress | None:
        statement = select(CustomerAddress).where(
            CustomerAddress.customer_id == customer_id,
            CustomerAddress.is_default.is_(True),
            CustomerAddress.is_active.is_(True),
        )

        return self.db.scalar(statement)

    def create(
        self,
        address: CustomerAddress,
    ) -> CustomerAddress:
        self.db.add(address)
        self.db.flush()

        return address

    def clear_default_address(
        self,
        customer_id: int,
    ) -> None:
        statement = (
            update(CustomerAddress)
            .where(
                CustomerAddress.customer_id == customer_id,
                CustomerAddress.is_default.is_(True),
            )
            .values(is_default=False)
        )

        self.db.execute(statement)
        self.db.flush()

    def save(self) -> None:
        self.db.flush()

    def delete(
        self,
        address: CustomerAddress,
    ) -> None:
        self.db.delete(address)
        self.db.flush()