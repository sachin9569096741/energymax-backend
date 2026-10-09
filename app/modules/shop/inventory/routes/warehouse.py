from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.shop.inventory.schemas.warehouse import (
    WarehouseCreate,
    WarehouseListResponse,
    WarehouseResponse,
    WarehouseUpdate,
)
from app.modules.shop.inventory.services.warehouse import WarehouseService


router = APIRouter(
    prefix="/warehouses",
    tags=["Inventory - Warehouses"],
)


# ---------------------------------------------------------------------------
# LIST WAREHOUSES
# ---------------------------------------------------------------------------

@router.get(
    "",
    response_model=WarehouseListResponse,
)
def list_warehouses(
    active_only: bool = Query(default=False),
    db: Session = Depends(get_db),
):
    service = WarehouseService(db)

    warehouses = service.list(
        active_only=active_only,
    )

    return WarehouseListResponse(
        items=warehouses,
        total=len(warehouses),
    )


# ---------------------------------------------------------------------------
# GET WAREHOUSE
# ---------------------------------------------------------------------------

@router.get(
    "/{public_id}",
    response_model=WarehouseResponse,
)
def get_warehouse(
    public_id: str,
    db: Session = Depends(get_db),
):
    service = WarehouseService(db)

    return service.get_by_public_id(
        public_id,
    )


# ---------------------------------------------------------------------------
# CREATE WAREHOUSE
# ---------------------------------------------------------------------------

@router.post(
    "",
    response_model=WarehouseResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_warehouse(
    payload: WarehouseCreate,
    db: Session = Depends(get_db),
):
    service = WarehouseService(db)

    warehouse = service.create(
        name=payload.name,
        code=payload.code,
        address=payload.address,
    )

    db.commit()

    return warehouse


# ---------------------------------------------------------------------------
# UPDATE WAREHOUSE
# ---------------------------------------------------------------------------

@router.patch(
    "/{public_id}",
    response_model=WarehouseResponse,
)
def update_warehouse(
    public_id: str,
    payload: WarehouseUpdate,
    db: Session = Depends(get_db),
):
    service = WarehouseService(db)

    warehouse = service.update(
        public_id,
        name=payload.name,
        code=payload.code,
        address=payload.address,
        is_active=payload.is_active,
    )

    db.commit()

    return warehouse