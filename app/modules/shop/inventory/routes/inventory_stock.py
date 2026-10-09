from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db

from app.modules.shop.inventory.schemas.inventory_stock import (
    StockInRequest,
    StockOutRequest,
)

from app.modules.shop.inventory.schemas.inventory_stock_response import (
    StockOperationResponse,
)

from app.modules.shop.inventory.services.inventory_stock import (
    InventoryStockService,
)


router = APIRouter(
    prefix="/stock",
    tags=["Inventory - Stock"],
)


# ------------------------------------------------------------------
# STOCK IN
# ------------------------------------------------------------------

@router.post(
    "/in",
    response_model=StockOperationResponse,
)
def stock_in(
    payload: StockInRequest,
    db: Session = Depends(get_db),
):
    service = InventoryStockService(db)

    balance, movement = service.stock_in(
        warehouse_id=payload.warehouse_id,
        variant_id=payload.variant_id,
        quantity=payload.quantity,
        movement_type=payload.movement_type,
        reference_type=payload.reference_type,
        reference_id=payload.reference_id,
        idempotency_key=payload.idempotency_key,
        note=payload.note,
    )

    db.commit()

    db.refresh(balance)
    db.refresh(movement)

    available = (
        Decimal(balance.on_hand)
        - Decimal(balance.reserved)
        - Decimal(balance.damaged)
    )

    return StockOperationResponse(
        warehouse_id=balance.warehouse_id,
        variant_id=balance.variant_id,
        on_hand=balance.on_hand,
        reserved=balance.reserved,
        damaged=balance.damaged,
        available=available,
        movement_id=movement.id,
        movement_type=movement.movement_type,
        movement_quantity=movement.quantity,
        before_quantity=movement.before_quantity,
        after_quantity=movement.after_quantity,
        created_at=movement.created_at,
    )


# ------------------------------------------------------------------
# STOCK OUT
# ------------------------------------------------------------------

@router.post(
    "/out",
    response_model=StockOperationResponse,
)
def stock_out(
    payload: StockOutRequest,
    db: Session = Depends(get_db),
):
    service = InventoryStockService(db)

    balance, movement = service.stock_out(
        warehouse_id=payload.warehouse_id,
        variant_id=payload.variant_id,
        quantity=payload.quantity,
        movement_type=payload.movement_type,
        reference_type=payload.reference_type,
        reference_id=payload.reference_id,
        idempotency_key=payload.idempotency_key,
        note=payload.note,
    )

    db.commit()

    db.refresh(balance)
    db.refresh(movement)

    available = (
        Decimal(balance.on_hand)
        - Decimal(balance.reserved)
        - Decimal(balance.damaged)
    )

    return StockOperationResponse(
        warehouse_id=balance.warehouse_id,
        variant_id=balance.variant_id,
        on_hand=balance.on_hand,
        reserved=balance.reserved,
        damaged=balance.damaged,
        available=available,
        movement_id=movement.id,
        movement_type=movement.movement_type,
        movement_quantity=movement.quantity,
        before_quantity=movement.before_quantity,
        after_quantity=movement.after_quantity,
        created_at=movement.created_at,
    )