from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db

from app.modules.shop.catalog.models.product_variant import (
    ProductVariant,
)

from app.modules.shop.inventory.constants.enums import (
    StockAdjustmentType,
)

from app.modules.shop.inventory.repositories.warehouse import (
    WarehouseRepository,
)

from app.modules.shop.inventory.schemas.stock_adjustment import (
    StockAdjustmentCreateRequest,
    StockAdjustmentListResponse,
    StockAdjustmentResponse,
)

from app.modules.shop.inventory.services.stock_adjustment import (
    StockAdjustmentService,
)


router = APIRouter(
    prefix="/adjustments",
    tags=["Inventory Adjustments"],
)


# ------------------------------------------------------------------
# CREATE STOCK ADJUSTMENT
# ------------------------------------------------------------------

@router.post(
    "",
    response_model=StockAdjustmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_adjustment(
    payload: StockAdjustmentCreateRequest,
    db: Session = Depends(get_db),
):
    # --------------------------------------------------------------
    # RESOLVE WAREHOUSE PUBLIC ID
    # --------------------------------------------------------------

    warehouse = WarehouseRepository(db).get_by_public_id(
        payload.warehouse_id
    )

    if not warehouse:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Warehouse not found",
        )

    if not warehouse.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Warehouse is inactive",
        )

    # --------------------------------------------------------------
    # RESOLVE VARIANT PUBLIC ID
    # --------------------------------------------------------------

    variant = (
        db.query(ProductVariant)
        .filter(
            ProductVariant.public_id == payload.variant_id
        )
        .first()
    )

    if not variant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product variant not found",
        )

    if not variant.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Product variant is inactive",
        )

    # --------------------------------------------------------------
    # SERVICE
    # --------------------------------------------------------------

    service = StockAdjustmentService(db)

    adjustment = service.create(
        warehouse_id=warehouse.id,
        variant_id=variant.id,
        adjustment_type=payload.adjustment_type,
        quantity=payload.quantity,
        reason=payload.reason,
        idempotency_key=payload.idempotency_key,
    )

    # --------------------------------------------------------------
    # COMMIT
    # --------------------------------------------------------------

    db.commit()

    db.refresh(adjustment)

    return adjustment


# ------------------------------------------------------------------
# GET ADJUSTMENT
# ------------------------------------------------------------------

@router.get(
    "/{public_id}",
    response_model=StockAdjustmentResponse,
)
def get_adjustment(
    public_id: str,
    db: Session = Depends(get_db),
):
    service = StockAdjustmentService(db)

    return service.get_by_public_id(public_id)


# ------------------------------------------------------------------
# LIST ADJUSTMENTS
# ------------------------------------------------------------------

@router.get(
    "",
    response_model=StockAdjustmentListResponse,
)
def list_adjustments(
    warehouse_id: str | None = Query(
        default=None,
        description="Warehouse public UUID",
    ),
    variant_id: str | None = Query(
        default=None,
        description="Product variant public UUID",
    ),
    adjustment_type: StockAdjustmentType | None = Query(
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
    # RESOLVE WAREHOUSE
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
    # RESOLVE VARIANT
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

    service = StockAdjustmentService(db)

    adjustments = service.list(
        warehouse_id=warehouse_internal_id,
        variant_id=variant_internal_id,
        adjustment_type=adjustment_type,
        limit=limit,
        offset=offset,
    )

    return StockAdjustmentListResponse(
        items=adjustments,
        total=len(adjustments),
    )