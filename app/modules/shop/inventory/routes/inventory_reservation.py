from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db

from app.modules.shop.catalog.models.product_variant import (
    ProductVariant,
)

from app.modules.shop.inventory.models.inventory_reservation import (
    InventoryReservation,
)

from app.modules.shop.inventory.models.warehouse import Warehouse

from app.modules.shop.inventory.schemas.inventory_reservation import (
    ReservationCreateRequest,
    ReservationListResponse,
    ReservationResponse,
)

from app.modules.shop.inventory.services.inventory_reservation import (
    InventoryReservationService,
)


router = APIRouter(
    prefix="/reservations",
    tags=["Inventory - Reservations"],
)


# ================================================================
# CREATE RESERVATION
# ================================================================

@router.post(
    "",
    response_model=ReservationResponse,
    status_code=201,
)
def create_reservation(
    payload: ReservationCreateRequest,
    db: Session = Depends(get_db),
):
    warehouse = db.execute(
        select(Warehouse).where(
            Warehouse.public_id == payload.warehouse_id
        )
    ).scalar_one_or_none()

    if not warehouse:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=404,
            detail="Warehouse not found",
        )

    variant = db.execute(
        select(ProductVariant).where(
            ProductVariant.public_id == payload.variant_id
        )
    ).scalar_one_or_none()

    if not variant:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=404,
            detail="Product variant not found",
        )

    service = InventoryReservationService(db)

    reservation = service.create(
        warehouse_id=warehouse.id,
        variant_id=variant.id,
        quantity=payload.quantity,
        reference_type=payload.reference_type,
        reference_id=payload.reference_id,
        idempotency_key=payload.idempotency_key,
        
    )

    db.commit()
    db.refresh(reservation)

    return reservation


# ================================================================
# LIST RESERVATIONS
# ================================================================

@router.get(
    "",
    response_model=ReservationListResponse,
)
def list_reservations(
    warehouse_id: str | None = Query(default=None),
    variant_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    reference_type: str | None = Query(default=None),
    reference_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    warehouse_internal_id = None
    variant_internal_id = None

    if warehouse_id:
        warehouse = db.execute(
            select(Warehouse).where(
                Warehouse.public_id == warehouse_id
            )
        ).scalar_one_or_none()

        if not warehouse:
            from fastapi import HTTPException

            raise HTTPException(
                status_code=404,
                detail="Warehouse not found",
            )

        warehouse_internal_id = warehouse.id

    if variant_id:
        variant = db.execute(
            select(ProductVariant).where(
                ProductVariant.public_id == variant_id
            )
        ).scalar_one_or_none()

        if not variant:
            from fastapi import HTTPException

            raise HTTPException(
                status_code=404,
                detail="Product variant not found",
            )

        variant_internal_id = variant.id

    service = InventoryReservationService(db)

    reservations = service.reservation_repository.list(
        warehouse_id=warehouse_internal_id,
        variant_id=variant_internal_id,
        status=status,
        reference_type=reference_type,
        reference_id=reference_id,
        limit=limit,
        offset=offset,
    )

    return ReservationListResponse(
        items=reservations,
        total=len(reservations),
    )


# ================================================================
# GET RESERVATION
# ================================================================

@router.get(
    "/{reservation_id}",
    response_model=ReservationResponse,
)
def get_reservation(
    reservation_id: int,
    db: Session = Depends(get_db),
):
    service = InventoryReservationService(db)

    return service.get_by_id(reservation_id)


# ================================================================
# RELEASE RESERVATION
# ================================================================

@router.post(
    "/{reservation_id}/release",
    response_model=ReservationResponse,
)
def release_reservation(
    reservation_id: int,
    db: Session = Depends(get_db),
):
    service = InventoryReservationService(db)

    reservation = service.release(
        reservation_id=reservation_id
    )

    db.commit()
    db.refresh(reservation)

    return reservation


# ================================================================
# CONFIRM RESERVATION
# ================================================================

@router.post(
    "/{reservation_id}/confirm",
    response_model=ReservationResponse,
)
def confirm_reservation(
    reservation_id: int,
    db: Session = Depends(get_db),
):
    service = InventoryReservationService(db)

    reservation = service.confirm(
        reservation_id=reservation_id
    )

    db.commit()
    db.refresh(reservation)

    return reservation