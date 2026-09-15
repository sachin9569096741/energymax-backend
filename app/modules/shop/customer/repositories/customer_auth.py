from sqlalchemy import select
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from sqlalchemy import update
from app.modules.shop.customer.models.customer import Customer
from app.modules.shop.customer.models.customer_session import CustomerSession
from app.modules.shop.customer.models.customer_otp import CustomerOTP


class CustomerAuthRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_customer_by_username(
        self,
        username: str,
    ) -> Customer | None:
        statement = select(Customer).where(
            Customer.username == username
        )
        return self.db.scalar(statement)

    def get_customer_by_email(
        self,
        email: str,
    ) -> Customer | None:
        statement = select(Customer).where(
            Customer.email == email
        )
        return self.db.scalar(statement)

    def get_customer_by_phone(
        self,
        phone: str,
    ) -> Customer | None:
        statement = select(Customer).where(
            Customer.phone == phone
        )
        return self.db.scalar(statement)

    def get_customer_by_identifier(
        self,
        identifier: str,
    ) -> Customer | None:
        statement = select(Customer).where(
            (Customer.username == identifier)
            | (Customer.email == identifier)
            | (Customer.phone == identifier)
        )
        return self.db.scalar(statement)

    def get_customer_by_id(
        self,
        customer_id: int,
    ) -> Customer | None:
        statement = select(Customer).where(
            Customer.id == customer_id
        )
        return self.db.scalar(statement)

    def create_customer(
        self,
        customer: Customer,
    ) -> Customer:
        self.db.add(customer)
        self.db.flush()
        return customer

    def create_session(
        self,
        session: CustomerSession,
    ) -> CustomerSession:
        self.db.add(session)
        self.db.flush()
        return session

    def create_otp(
        self,
        otp: CustomerOTP,
    ) -> CustomerOTP:
        self.db.add(otp)
        self.db.flush()
        return otp

    def get_session_by_token_hash(
        self,
        token_hash: str,
    ) -> CustomerSession | None:
        statement = select(CustomerSession).where(
            CustomerSession.token_hash == token_hash
        )
        return self.db.scalar(statement)

    def save(self) -> None:
        self.db.flush()


    def invalidate_active_otps(
        self,
        destination: str,
        channel: str,
        purpose: str,
    ) -> None:
        statement = (
            update(CustomerOTP)
            .where(
                CustomerOTP.destination == destination,
                CustomerOTP.channel == channel,
                CustomerOTP.purpose == purpose,
                CustomerOTP.consumed_at.is_(None),
                CustomerOTP.expires_at > datetime.now(timezone.utc),
            )
            .values(
                consumed_at=datetime.now(timezone.utc),
            )
        )

        self.db.execute(statement)
        self.db.flush()


    def get_latest_otp(
        self,
        destination: str,
        channel: str,
        purpose: str,
    ) -> CustomerOTP | None:
        statement = (
            select(CustomerOTP)
            .where(
                CustomerOTP.destination == destination,
                CustomerOTP.channel == channel,
                CustomerOTP.purpose == purpose,
            )
            .order_by(CustomerOTP.created_at.desc())
            .limit(1)
        )

        return self.db.scalar(statement)


    def revoke_session(self, token_hash: str) -> bool:
        session = self.get_session_by_token_hash(token_hash)

        if session is None:
            return False

        session.is_active = False
        session.revoked_at = datetime.now(timezone.utc)

        self.db.flush()
        return True