
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.admin.auth.models.admin_user import AdminUser
from app.modules.admin.auth.security.dependencies import require_permission
from app.modules.shop.customer.models.customer import Customer
from app.modules.shop.customer.models.customer_session import CustomerSession
from app.modules.shop.order.models.order import Order


router = APIRouter(
    prefix="/admin/customers",
    tags=["Admin - Customers"],
)

# Orders that count toward returning-customer classification.
QUALIFYING_ORDER_STATUSES = (
    "paid",
    "confirmed",
    "processing",
    "packed",
    "shipped",
    "out_for_delivery",
    "delivered",
)


def customer_payload(customer: Customer, order_count: int = 0) -> dict:
    return {
        "public_id": customer.public_id,
        "username": customer.username,
        "first_name": customer.first_name,
        "last_name": customer.last_name,
        "email": customer.email,
        "phone": customer.phone,
        "email_verified": customer.email_verified,
        "phone_verified": customer.phone_verified,
        "is_active": customer.is_active,
        "created_at": customer.created_at,
        "last_login_at": customer.last_login_at,
        "order_count": order_count,
    }


def base_customer_query(search: str | None = None):
    query = select(Customer)

    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.where(
            or_(
                Customer.first_name.ilike(term),
                Customer.last_name.ilike(term),
                Customer.username.ilike(term),
                Customer.email.ilike(term),
                Customer.phone.ilike(term),
            )
        )

    return query


def qualifying_order_counts():
    return (
        select(
            Order.customer_id.label("customer_id"),
            func.count(Order.id).label("order_count"),
        )
        .where(Order.status.in_(QUALIFYING_ORDER_STATUSES))
        .group_by(Order.customer_id)
        .having(func.count(Order.id) >= 2)
        .subquery()
    )


# ---------------------------------------------------------
# GET /admin/customers/stats
# ---------------------------------------------------------
@router.get(
    "/stats",
    dependencies=[Depends(require_permission("customers.view"))],
)
def customer_stats(db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    new_since = now - timedelta(days=30)

    total_customers = (
        db.scalar(
            select(func.count())
            .select_from(Customer)
            .where(Customer.is_active.is_(True))
        )
        or 0
    )

    new_customers = (
        db.scalar(
            select(func.count())
            .select_from(Customer)
            .where(
                Customer.is_active.is_(True),
                Customer.created_at >= new_since,
            )
        )
        or 0
    )

    returning = qualifying_order_counts()

    returning_customers = (
        db.scalar(
            select(func.count())
            .select_from(Customer)
            .join(
                returning,
                returning.c.customer_id == Customer.id,
            )
            .where(Customer.is_active.is_(True))
        )
        or 0
    )

    return {
        "total_customers": total_customers,
        "new_customers_last_30_days": new_customers,
        "returning_customers": returning_customers,
    }


# ---------------------------------------------------------
# GET /admin/customers
# All customers, with search and pagination
# ---------------------------------------------------------
@router.get(
    "",
    dependencies=[Depends(require_permission("customers.view"))],
)
def list_customers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, max_length=100),
    include_inactive: bool = False,
    db: Session = Depends(get_db),
):
    query = base_customer_query(search)

    if not include_inactive:
        query = query.where(Customer.is_active.is_(True))

    total = (
        db.scalar(
            select(func.count())
            .select_from(query.order_by(None).subquery())
        )
        or 0
    )

    customers = db.scalars(
        query.order_by(Customer.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    customer_ids = [customer.id for customer in customers]
    counts = {}

    if customer_ids:
        rows = db.execute(
            select(
                Order.customer_id,
                func.count(Order.id),
            )
            .where(
                Order.customer_id.in_(customer_ids),
                Order.status.in_(QUALIFYING_ORDER_STATUSES),
            )
            .group_by(Order.customer_id)
        ).all()

        counts = {
            customer_id: count
            for customer_id, count in rows
        }

    return {
        "items": [
            customer_payload(customer, counts.get(customer.id, 0))
            for customer in customers
        ],
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": (total + page_size - 1) // page_size,
    }


# ---------------------------------------------------------
# GET /admin/customers/new
# Customers registered within the last N days
# ---------------------------------------------------------
@router.get(
    "/new",
    dependencies=[Depends(require_permission("customers.view"))],
)
def list_new_customers(
    days: int = Query(30, ge=1, le=365),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    since = datetime.now(timezone.utc) - timedelta(days=days)

    query = select(Customer).where(
        Customer.is_active.is_(True),
        Customer.created_at >= since,
    )

    total = (
        db.scalar(
            select(func.count())
            .select_from(query.subquery())
        )
        or 0
    )

    customers = db.scalars(
        query.order_by(Customer.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    return {
        "items": [customer_payload(c) for c in customers],
        "days": days,
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": (total + page_size - 1) // page_size,
    }


# ---------------------------------------------------------
# GET /admin/customers/returning
# Customers with at least 2 qualifying orders
# ---------------------------------------------------------
@router.get(
    "/returning",
    dependencies=[Depends(require_permission("customers.view"))],
)
def list_returning_customers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    order_counts = qualifying_order_counts()

    total = (
        db.scalar(
            select(func.count())
            .select_from(Customer)
            .join(
                order_counts,
                order_counts.c.customer_id == Customer.id,
            )
            .where(Customer.is_active.is_(True))
        )
        or 0
    )

    rows = db.execute(
        select(Customer, order_counts.c.order_count)
        .join(
            order_counts,
            order_counts.c.customer_id == Customer.id,
        )
        .where(Customer.is_active.is_(True))
        .order_by(
            order_counts.c.order_count.desc(),
            Customer.created_at.desc(),
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    return {
        "items": [
            customer_payload(customer, order_count)
            for customer, order_count in rows
        ],
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": (total + page_size - 1) // page_size,
    }


# ---------------------------------------------------------
# GET /admin/customers/{customer_public_id}
# Customer details
# ---------------------------------------------------------
@router.get(
    "/{customer_public_id}",
    dependencies=[Depends(require_permission("customers.view"))],
)
def get_customer(
    customer_public_id: str,
    db: Session = Depends(get_db),
):
    customer = db.scalar(
        select(Customer).where(
            Customer.public_id == customer_public_id
        )
    )

    if customer is None:
        raise HTTPException(
            status_code=404,
            detail="Customer not found.",
        )

    order_count = (
        db.scalar(
            select(func.count(Order.id)).where(
                Order.customer_id == customer.id,
                Order.status.in_(QUALIFYING_ORDER_STATUSES),
            )
        )
        or 0
    )

    return customer_payload(customer, order_count)


# ---------------------------------------------------------
# DELETE /admin/customers/{customer_public_id}
# Deactivate account and release identifiers
# ---------------------------------------------------------
@router.delete(
    "/{customer_public_id}",
    dependencies=[Depends(require_permission("customers.delete"))],
)
def delete_customer(
    customer_public_id: str,
    db: Session = Depends(get_db),
):
    try:
        customer = db.scalar(
            select(Customer)
            .where(Customer.public_id == customer_public_id)
            .with_for_update()
        )

        if customer is None:
            raise HTTPException(
                status_code=404,
                detail="Customer not found.",
            )

        if not customer.is_active:
            return {
                "message": "Customer account is already deactivated.",
                "public_id": customer.public_id,
            }

        old_public_id = customer.public_id
        now = datetime.now(timezone.utc)

        # Preserve order and financial history.
        # Release identifiers so a new account can reuse them.
        customer.is_active = False
        customer.email = None
        customer.phone = None
        customer.username = f"deleted-{old_public_id}"
        customer.password_hash = None
        customer.email_verified = False
        customer.phone_verified = False

        # Revoke all active sessions.
        db.query(CustomerSession).filter(
            CustomerSession.customer_id == customer.id,
            CustomerSession.is_active.is_(True),
        ).update(
            {
                "is_active": False,
                "revoked_at": now,
            },
            synchronize_session=False,
        )

        db.commit()

        return {
            "message": (
                "Customer account deactivated. "
                "Order history preserved and identifiers released."
            ),
            "public_id": old_public_id,
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise
