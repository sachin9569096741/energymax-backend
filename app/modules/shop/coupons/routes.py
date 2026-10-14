from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.admin.auth.security.dependencies import get_current_admin
from app.modules.shop.customer.security.dependencies import get_current_customer

from app.modules.shop.coupons.models.coupon import Coupon
from app.modules.shop.coupons.models.coupon_redemption import CouponRedemption
from app.modules.shop.coupons.schemas import (
    ApplyCouponRequest,
    CouponApplyResponse,
    CouponCreate,
    CouponResponse,
    CouponUpdate,
)
from app.modules.shop.coupons.service import CouponService


customer_router = APIRouter(
    prefix="/checkout",
    tags=["Shop - Coupons"],
)

admin_router = APIRouter(
    prefix="/admin/coupons",
    tags=["Admin - Coupons"],
)


# CUSTOMER: APPLY COUPON
@customer_router.post(
    "/{checkout_public_id}/coupon",
    response_model=CouponApplyResponse,
)
def apply_coupon(
    checkout_public_id: str,
    data: ApplyCouponRequest,
    current_customer=Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    result = CouponService(db).apply(
        checkout_public_id,
        current_customer.id,
        data.code,
    )

    db.commit()
    return result


# CUSTOMER: REMOVE COUPON
@customer_router.delete(
    "/{checkout_public_id}/coupon",
    response_model=CouponApplyResponse,
)
def remove_coupon(
    checkout_public_id: str,
    current_customer=Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    result = CouponService(db).remove(
        checkout_public_id,
        current_customer.id,
    )

    db.commit()
    return result


# ADMIN: CREATE COUPON
@admin_router.post(
    "",
    response_model=CouponResponse,
    status_code=201,
)
def create_coupon(
    data: CouponCreate,
    _admin=Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    code = data.code.strip().upper()

    existing = db.scalar(
        select(Coupon.id).where(Coupon.code == code)
    )

    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail="A coupon with this code already exists.",
        )

    values = data.model_dump()
    values["code"] = code

    coupon = Coupon(**values)
    db.add(coupon)
    db.commit()
    db.refresh(coupon)

    return coupon


# ADMIN: LIST COUPONS
@admin_router.get(
    "",
    response_model=list[CouponResponse],
)
def list_coupons(
    _admin=Depends(get_current_admin),
    db: Session = Depends(get_db),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    return list(
        db.scalars(
            select(Coupon)
            .order_by(Coupon.created_at.desc())
            .limit(limit)
            .offset(offset)
        ).all()
    )


# ADMIN: GET SINGLE COUPON
@admin_router.get(
    "/{coupon_public_id}",
    response_model=CouponResponse,
)
def get_coupon(
    coupon_public_id: str,
    _admin=Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    coupon = db.scalar(
        select(Coupon).where(
            Coupon.public_id == coupon_public_id
        )
    )

    if coupon is None:
        raise HTTPException(404, "Coupon not found.")

    return coupon


# ADMIN: UPDATE COUPON
@admin_router.patch(
    "/{coupon_public_id}",
    response_model=CouponResponse,
)
def update_coupon(
    coupon_public_id: str,
    data: CouponUpdate,
    _admin=Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    coupon = db.scalar(
        select(Coupon)
        .where(Coupon.public_id == coupon_public_id)
        .with_for_update()
    )

    if coupon is None:
        raise HTTPException(404, "Coupon not found.")

    changes = data.model_dump(exclude_unset=True)

    if (
        "discount_percent" in changes
        and changes["discount_percent"] not in (5, 10)
    ):
        raise HTTPException(
            422,
            "discount_percent must be 5 or 10",
        )

    for key, value in changes.items():
        setattr(coupon, key, value)

    db.commit()
    db.refresh(coupon)

    return coupon


# ADMIN: ACTIVATE COUPON
@admin_router.post(
    "/{coupon_public_id}/activate",
    response_model=CouponResponse,
)
def activate_coupon(
    coupon_public_id: str,
    _admin=Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    coupon = db.scalar(
        select(Coupon)
        .where(Coupon.public_id == coupon_public_id)
        .with_for_update()
    )

    if coupon is None:
        raise HTTPException(404, "Coupon not found.")

    coupon.is_active = True
    db.commit()
    db.refresh(coupon)

    return coupon


# ADMIN: DEACTIVATE COUPON
@admin_router.post(
    "/{coupon_public_id}/deactivate",
    response_model=CouponResponse,
)
def deactivate_coupon(
    coupon_public_id: str,
    _admin=Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    coupon = db.scalar(
        select(Coupon)
        .where(Coupon.public_id == coupon_public_id)
        .with_for_update()
    )

    if coupon is None:
        raise HTTPException(404, "Coupon not found.")

    coupon.is_active = False
    db.commit()
    db.refresh(coupon)

    return coupon


# ADMIN: VIEW REDEMPTIONS
@admin_router.get(
    "/{coupon_public_id}/redemptions",
)
def list_redemptions(
    coupon_public_id: str,
    _admin=Depends(get_current_admin),
    db: Session = Depends(get_db),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    coupon = db.scalar(
        select(Coupon).where(
            Coupon.public_id == coupon_public_id
        )
    )

    if coupon is None:
        raise HTTPException(404, "Coupon not found.")

    rows = db.scalars(
        select(CouponRedemption)
        .where(CouponRedemption.coupon_id == coupon.id)
        .order_by(CouponRedemption.created_at.desc())
        .limit(limit)
        .offset(offset)
    ).all()

    return [
        {
            "id": row.id,
            "coupon_code": coupon.code,
            "customer_id": row.customer_id,
            "checkout_id": row.checkout_id,
            "order_id": row.order_id,
            "status": row.status,
            "discount_amount": row.discount_amount,
            "reserved_until": row.reserved_until,
            "redeemed_at": row.redeemed_at,
            "created_at": row.created_at,
        }
        for row in rows
    ]