from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.modules.shop.checkout.models.checkout import Checkout
from app.modules.shop.checkout.models.checkout_item import CheckoutItem
from app.modules.shop.customer.models.customer_address import CustomerAddress


class CheckoutRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_public_id(
        self,
        public_id: str,
        customer_id: int,
    ) -> Checkout | None:
        statement = (
            select(Checkout)
            .options(
                selectinload(Checkout.items)
            )
            .where(
                Checkout.public_id == public_id,
                Checkout.customer_id == customer_id,
            )
        )

        return self.db.scalar(statement)

    def get_by_id(
        self,
        checkout_id: int,
        customer_id: int,
    ) -> Checkout | None:
        statement = (
            select(Checkout)
            .options(
                selectinload(Checkout.items)
            )
            .where(
                Checkout.id == checkout_id,
                Checkout.customer_id == customer_id,
            )
        )

        return self.db.scalar(statement)

    def get_active_checkout(
        self,
        customer_id: int,
    ) -> Checkout | None:
        statement = (
            select(Checkout)
            .options(
                selectinload(Checkout.items)
            )
            .where(
                Checkout.customer_id == customer_id,
                Checkout.status == "created",
            )
            .order_by(Checkout.created_at.desc())
            .limit(1)
        )

        return self.db.scalar(statement)

    def get_customer_address(
        self,
        address_public_id: str,
        customer_id: int,
    ) -> CustomerAddress | None:
        statement = (
            select(CustomerAddress)
            .where(
                CustomerAddress.public_id == address_public_id,
                CustomerAddress.customer_id == customer_id,
            )
        )

        return self.db.scalar(statement)

    def get_customer_address_by_id(
        self,
        address_id: int,
        customer_id: int,
    ) -> CustomerAddress | None:
        statement = (
            select(CustomerAddress)
            .where(
                CustomerAddress.id == address_id,
                CustomerAddress.customer_id == customer_id,
                CustomerAddress.is_active.is_(True),
            )
        )
        return self.db.scalar(statement)

    def create(self, checkout: Checkout) -> Checkout:
        self.db.add(checkout)
        self.db.flush()
        return checkout

    def save(self) -> None:
        self.db.flush()

    def delete(self, checkout: Checkout) -> None:
        self.db.delete(checkout)
        self.db.flush()