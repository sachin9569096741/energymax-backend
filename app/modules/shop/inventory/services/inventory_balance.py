from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.shop.inventory.models.inventory_balance import (
    InventoryBalance,
)
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.modules.shop.catalog.models.product_variant import ProductVariant
from app.modules.shop.inventory.models.warehouse import Warehouse
from app.modules.shop.inventory.repositories.inventory_balance import (
    InventoryBalanceRepository,
)


class InventoryBalanceService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = InventoryBalanceRepository(db)

    # ------------------------------------------------------------------
    # GET BALANCE
    # ------------------------------------------------------------------

    def get_balance(
        self,
        warehouse_id: int,
        variant_id: int,
    ) -> InventoryBalance:

        balance = self.repository.get_by_warehouse_and_variant(
            warehouse_id=warehouse_id,
            variant_id=variant_id,
        )

        if not balance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Inventory balance not found",
            )

        return balance

    # ------------------------------------------------------------------
    # GET BALANCE FOR UPDATE
    # ------------------------------------------------------------------

    def get_balance_for_update(
        self,
        warehouse_id: int,
        variant_id: int,
    ) -> InventoryBalance:

        balance = self.repository.get_for_update(
            warehouse_id=warehouse_id,
            variant_id=variant_id,
        )

        if not balance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Inventory balance not found",
            )

        return balance

    # ------------------------------------------------------------------
    # CREATE BALANCE
    # ------------------------------------------------------------------

    def create_balance(
        self,
        *,
        warehouse_id: int,
        variant_id: int,
        on_hand: Decimal = Decimal("0"),
        reserved: Decimal = Decimal("0"),
        damaged: Decimal = Decimal("0"),
        incoming: Decimal = Decimal("0"),
        reorder_level: Decimal = Decimal("0"),
        reorder_quantity: Decimal = Decimal("0"),
        safety_stock: Decimal = Decimal("0"),
    ) -> InventoryBalance:

        values = [
            on_hand,
            reserved,
            damaged,
            incoming,
            reorder_level,
            reorder_quantity,
            safety_stock,
        ]

        if any(value < 0 for value in values):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inventory quantities cannot be negative",
            )

        existing = self.repository.get_by_warehouse_and_variant(
            warehouse_id=warehouse_id,
            variant_id=variant_id,
        )

        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Inventory balance already exists",
            )

        try:
            return self.repository.create(
                warehouse_id=warehouse_id,
                variant_id=variant_id,
                on_hand=on_hand,
                reserved=reserved,
                damaged=damaged,
                incoming=incoming,
                reorder_level=reorder_level,
                reorder_quantity=reorder_quantity,
                safety_stock=safety_stock,
            )

        except IntegrityError:
            self.db.rollback()

            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Inventory balance already exists",
            )

    # ------------------------------------------------------------------
    # UPDATE SETTINGS
    # ------------------------------------------------------------------

    def update_settings(
        self,
        *,
        warehouse_id: int,
        variant_id: int,
        reorder_level: Decimal | None = None,
        reorder_quantity: Decimal | None = None,
        safety_stock: Decimal | None = None,
    ) -> InventoryBalance:

        balance = self.get_balance(
            warehouse_id=warehouse_id,
            variant_id=variant_id,
        )

        values = [
            reorder_level,
            reorder_quantity,
            safety_stock,
        ]

        if any(
            value is not None and value < 0
            for value in values
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inventory settings cannot be negative",
            )

        return self.repository.update(
            balance,
            reorder_level=reorder_level,
            reorder_quantity=reorder_quantity,
            safety_stock=safety_stock,
        )

    # ------------------------------------------------------------------
    # AVAILABLE STOCK
    # ------------------------------------------------------------------

    def get_available(
        self,
        warehouse_id: int,
        variant_id: int,
    ) -> Decimal:

        balance = self.get_balance(
            warehouse_id=warehouse_id,
            variant_id=variant_id,
        )

        return self.repository.get_available(balance)

    # ------------------------------------------------------------------
    # CHECK STOCK
    # ------------------------------------------------------------------

    def check_available(
        self,
        *,
        warehouse_id: int,
        variant_id: int,
        quantity: Decimal,
    ) -> bool:

        if quantity <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Quantity must be greater than zero",
            )

        balance = self.get_balance(
            warehouse_id=warehouse_id,
            variant_id=variant_id,
        )

        return self.repository.has_available_stock(
            balance,
            quantity,
        )

    # ------------------------------------------------------------------
    # LIST WAREHOUSE INVENTORY
    # ------------------------------------------------------------------

    def list_by_warehouse(
        self,
        warehouse_id: int,
    ) -> list[InventoryBalance]:

        return self.repository.list_by_warehouse(
            warehouse_id
        )

    # ------------------------------------------------------------------
    # LIST VARIANT INVENTORY
    # ------------------------------------------------------------------

    def list_by_variant(
        self,
        variant_id: int,
    ) -> list[InventoryBalance]:

        return self.repository.list_by_variant(
            variant_id
        )


    def list_detailed(
        self,
        *,
        warehouse_id: int | None = None,
        variant_id: int | None = None,
    ) -> list[InventoryBalance]:

        query = (
            select(InventoryBalance)
            .options(
                joinedload(InventoryBalance.warehouse),
                joinedload(InventoryBalance.variant).joinedload(
                    ProductVariant.product
                ),
            )
            .order_by(InventoryBalance.id.desc())
        )

        if warehouse_id is not None:
            query = query.where(
                InventoryBalance.warehouse_id == warehouse_id
            )

        if variant_id is not None:
            query = query.where(
                InventoryBalance.variant_id == variant_id
            )

        result = self.db.execute(query)

        return list(result.unique().scalars().all())


    def count_detailed(
        self,
        *,
        warehouse_id: int | None = None,
        variant_id: int | None = None,
    ) -> int:

        balances = self.list_detailed(
            warehouse_id=warehouse_id,
            variant_id=variant_id,
        )

        return len(balances)