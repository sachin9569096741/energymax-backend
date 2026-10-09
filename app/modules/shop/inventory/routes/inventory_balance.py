from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db

from app.modules.shop.catalog.models.product_variant import (
    ProductVariant,
)

from app.modules.shop.inventory.models.warehouse import Warehouse

from app.modules.shop.inventory.schemas.inventory_balance import (
    InventoryBalanceListResponse,
    InventoryBalanceResponse,
)

from app.modules.shop.inventory.services.inventory_balance import (
    InventoryBalanceService,
)


router = APIRouter(
    prefix="/balances",
    tags=["Inventory - Balances"],
)


@router.get(
    "",
    response_model=InventoryBalanceListResponse,
)
def list_inventory_balances(
    warehouse_id: str | None = Query(default=None),
    variant_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    service = InventoryBalanceService(db)

    warehouse_internal_id = None
    variant_internal_id = None

    # Resolve warehouse public UUID
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

    # Resolve variant public UUID
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

    balances = service.list_detailed(
        warehouse_id=warehouse_internal_id,
        variant_id=variant_internal_id,
    )

    items = []

    for balance in balances:
        available = (
            Decimal(balance.on_hand)
            - Decimal(balance.reserved)
            - Decimal(balance.damaged)
        )

        items.append(
            InventoryBalanceResponse(
                product_id=balance.variant.product.id,
                product_name=balance.variant.product.name,

                variant_id=balance.variant.id,
                flavour=balance.variant.flavour,
                sku=balance.variant.sku,

                warehouse_id=balance.warehouse.id,
                warehouse_name=balance.warehouse.name,
                warehouse_code=balance.warehouse.code,

                on_hand=balance.on_hand,
                reserved=balance.reserved,
                damaged=balance.damaged,
                incoming=balance.incoming,
                available=available,

                reorder_level=balance.reorder_level,
                reorder_quantity=balance.reorder_quantity,
                safety_stock=balance.safety_stock,

                created_at=balance.created_at,
                updated_at=balance.updated_at,
            )
        )

    return InventoryBalanceListResponse(
        items=items,
        total=len(items),
    )



@router.get(
    "/{variant_public_id}",
    response_model=InventoryBalanceResponse,
)
def get_inventory_balance(
    variant_public_id: str,
    warehouse_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    service = InventoryBalanceService(db)

    variant = db.execute(
        select(ProductVariant)
        .where(
            ProductVariant.public_id == variant_public_id
        )
    ).scalar_one_or_none()

    if not variant:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=404,
            detail="Product variant not found",
        )

    warehouse_internal_id = None

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

    balance = service.get_balance(
        warehouse_id=warehouse_internal_id,
        variant_id=variant.id,
    )

    if not balance:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=404,
            detail="Inventory balance not found",
        )

    available = (
        Decimal(balance.on_hand)
        - Decimal(balance.reserved)
        - Decimal(balance.damaged)
    )

    return InventoryBalanceResponse(
        product_id=variant.product.id,
        product_name=variant.product.name,

        variant_id=variant.id,
        flavour=variant.flavour,
        sku=variant.sku,

        warehouse_id=balance.warehouse.id,
        warehouse_name=balance.warehouse.name,
        warehouse_code=balance.warehouse.code,

        on_hand=balance.on_hand,
        reserved=balance.reserved,
        damaged=balance.damaged,
        incoming=balance.incoming,
        available=available,

        reorder_level=balance.reorder_level,
        reorder_quantity=balance.reorder_quantity,
        safety_stock=balance.safety_stock,

        created_at=balance.created_at,
        updated_at=balance.updated_at,
    )