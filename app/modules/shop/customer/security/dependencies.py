from datetime import datetime, timezone

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.shop.customer.models.customer import Customer
from app.modules.shop.customer.models.customer_session import CustomerSession
from app.modules.shop.customer.security.security import hash_session_token


def get_current_customer(
    x_customer_session_token: str | None = Header(
        default=None,
        alias="X-Customer-Session-Token",
    ),
    db: Session = Depends(get_db),
) -> Customer:
    if not x_customer_session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Customer authentication required.",
        )

    token_hash = hash_session_token(x_customer_session_token)

    session = db.scalar(
        select(CustomerSession)
        .where(
            CustomerSession.token_hash == token_hash,
            CustomerSession.is_active.is_(True),
            CustomerSession.expires_at > datetime.now(timezone.utc),
        )
    )

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired customer session.",
        )

    customer = db.scalar(
        select(Customer).where(
            Customer.id == session.customer_id,
            Customer.is_active.is_(True),
        )
    )

    if customer is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Customer account is inactive or unavailable.",
        )

    session.last_used_at = datetime.now(timezone.utc)
    db.flush()

    return customer