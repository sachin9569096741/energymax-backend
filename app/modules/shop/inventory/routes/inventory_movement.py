from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db

from app.modules.shop.catalog.models.product_variant import ProductVariant

from app.modules.shop.inventory.constants.enums import (
    InventoryMovementType,
)

from app.modules.shop.inventory.models.inventory_movement import (
    InventoryMovement,
)

from app.modules.shop.inventory.repositories.inventory_movement import (
    InventoryMovementRepository,
)

from app.modules.shop.inventory.repositories.warehouse import (
    WarehouseRepository,
)

from app.modules.shop.inventory.schemas.inventory_movement import (
    InventoryMovementListResponse,
    InventoryMovementResponse,
)

from app.modules.shop.inventory.services.inventory_movement import (
    InventoryMovementService,
)

from sqlalchemy.orm import joinedload


router = APIRouter(
    prefix="/movements",
    tags=["Inventory Movements"],
)


# ------------------------------------------------------------------
# BUILD RESPONSE
# ------------------------------------------------------------------

def build_movement_response(
    movement: InventoryMovement,
) -> InventoryMovementResponse:

    variant = movement.variant
    product = variant.product
    warehouse = movement.warehouse

    return InventoryMovementResponse(
        id=movement.id,

        product_id=product.id,
        product_name=product.name,

        variant_id=variant.id,
        flavour=variant.flavour,
        sku=variant.sku,

        warehouse_id=warehouse.id,
        warehouse_name=warehouse.name,
        warehouse_code=warehouse.code,

        movement_type=movement.movement_type,

        quantity=movement.quantity,
        before_quantity=movement.before_quantity,
        after_quantity=movement.after_quantity,

        reference_type=movement.reference_type,
        reference_id=movement.reference_id,

        note=movement.note,

        created_at=movement.created_at,
    )


# ------------------------------------------------------------------
# LIST MOVEMENTS
# ------------------------------------------------------------------

@router.get(
    "",
    response_model=InventoryMovementListResponse,
)
def list_movements(
    warehouse_id: str | None = Query(
        default=None,
        description="Warehouse public UUID",
    ),
    variant_id: str | None = Query(
        default=None,
        description="Product variant public UUID",
    ),
    movement_type: InventoryMovementType | None = Query(
        default=None,
    ),
    reference_type: str | None = Query(
        default=None,
    ),
    reference_id: str | None = Query(
        default=None,
    ),
    limit: int = Query(
        default=100,
        ge=1,
        le=500,
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
    db: Session = Depends(get_db),
):

    warehouse_internal_id = None
    variant_internal_id = None

    # --------------------------------------------------------------
    # RESOLVE WAREHOUSE PUBLIC ID
    # --------------------------------------------------------------

    if warehouse_id:

        warehouse = WarehouseRepository(db).get_by_public_id(
            warehouse_id
        )

        if not warehouse:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Warehouse not found",
            )

        warehouse_internal_id = warehouse.id

    # --------------------------------------------------------------
    # RESOLVE VARIANT PUBLIC ID
    # --------------------------------------------------------------

    if variant_id:

        variant = (
            db.query(ProductVariant)
            .filter(
                ProductVariant.public_id == variant_id
            )
            .first()
        )

        if not variant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product variant not found",
            )

        variant_internal_id = variant.id

    # --------------------------------------------------------------
    # SERVICE
    # --------------------------------------------------------------

    service = InventoryMovementService(db)

    movements = service.list_detailed(
        warehouse_id=warehouse_internal_id,
        variant_id=variant_internal_id,
        movement_type=movement_type,
        reference_type=reference_type,
        reference_id=reference_id,
        limit=limit,
        offset=offset,
    )

    items = [
        build_movement_response(movement)
        for movement in movements
    ]

    return InventoryMovementListResponse(
        items=items,
        total=len(items),
    )


# ------------------------------------------------------------------
# GET SINGLE MOVEMENT
# ------------------------------------------------------------------

@router.get(
    "/{movement_id}",
    response_model=InventoryMovementResponse,
)
def get_movement(
    movement_id: int,
    db: Session = Depends(get_db),
):

    movement = (
        db.query(InventoryMovement)
        .options(
            joinedload(
                InventoryMovement.warehouse
            ),
            joinedload(
                InventoryMovement.variant
            ).joinedload(
                ProductVariant.product
            ),
        )
        .filter(
            InventoryMovement.id == movement_id
        )
        .first()
    )

    if not movement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory movement not found",
        )

    return build_movement_response(movement)