from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.shop.inventory.models.inventory_balance import (
    InventoryBalance,
)


class InventoryBalanceRepository:
    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # GET BY ID
    # ------------------------------------------------------------------

    def get_by_id(
        self,
        balance_id: int,
    ) -> Optional[InventoryBalance]:

        result = self.db.execute(
            select(InventoryBalance).where(
                InventoryBalance.id == balance_id
            )
        )

        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # GET BY WAREHOUSE + VARIANT
    # ------------------------------------------------------------------

    def get_by_warehouse_and_variant(
        self,
        warehouse_id: int,
        variant_id: int,
    ) -> Optional[InventoryBalance]:

        result = self.db.execute(
            select(InventoryBalance).where(
                InventoryBalance.warehouse_id == warehouse_id,
                InventoryBalance.variant_id == variant_id,
            )
        )

        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # GET + ROW LOCK
    # ------------------------------------------------------------------

    def get_for_update(
        self,
        warehouse_id: int,
        variant_id: int,
    ) -> Optional[InventoryBalance]:

        result = self.db.execute(
            select(InventoryBalance)
            .where(
                InventoryBalance.warehouse_id == warehouse_id,
                InventoryBalance.variant_id == variant_id,
            )
            .with_for_update()
        )

        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # CREATE
    # ------------------------------------------------------------------

    def create(
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

        balance = InventoryBalance(
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

        self.db.add(balance)
        self.db.flush()
        self.db.refresh(balance)

        return balance

    # ------------------------------------------------------------------
    # UPDATE
    # ------------------------------------------------------------------

    def update(
        self,
        balance: InventoryBalance,
        *,
        on_hand: Optional[Decimal] = None,
        reserved: Optional[Decimal] = None,
        damaged: Optional[Decimal] = None,
        incoming: Optional[Decimal] = None,
        reorder_level: Optional[Decimal] = None,
        reorder_quantity: Optional[Decimal] = None,
        safety_stock: Optional[Decimal] = None,
    ) -> InventoryBalance:

        if on_hand is not None:
            balance.on_hand = on_hand

        if reserved is not None:
            balance.reserved = reserved

        if damaged is not None:
            balance.damaged = damaged

        if incoming is not None:
            balance.incoming = incoming

        if reorder_level is not None:
            balance.reorder_level = reorder_level

        if reorder_quantity is not None:
            balance.reorder_quantity = reorder_quantity

        if safety_stock is not None:
            balance.safety_stock = safety_stock

        self.db.flush()
        self.db.refresh(balance)

        return balance

    # ------------------------------------------------------------------
    # AVAILABLE STOCK
    # ------------------------------------------------------------------

    @staticmethod
    def get_available(
        balance: InventoryBalance,
    ) -> Decimal:

        return (
            Decimal(balance.on_hand)
            - Decimal(balance.reserved)
            - Decimal(balance.damaged)
        )

    # ------------------------------------------------------------------
    # CHECK AVAILABLE STOCK
    # ------------------------------------------------------------------

    @staticmethod
    def has_available_stock(
        balance: InventoryBalance,
        quantity: Decimal,
    ) -> bool:

        available = (
            Decimal(balance.on_hand)
            - Decimal(balance.reserved)
            - Decimal(balance.damaged)
        )

        return available >= quantity

    # ------------------------------------------------------------------
    # LIST BY WAREHOUSE
    # ------------------------------------------------------------------

    def list_by_warehouse(
        self,
        warehouse_id: int,
    ) -> list[InventoryBalance]:

        result = self.db.execute(
            select(InventoryBalance)
            .where(
                InventoryBalance.warehouse_id == warehouse_id
            )
            .order_by(InventoryBalance.id.desc())
        )

        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # LIST BY VARIANT
    # ------------------------------------------------------------------

    def list_by_variant(
        self,
        variant_id: int,
    ) -> list[InventoryBalance]:

        result = self.db.execute(
            select(InventoryBalance)
            .where(
                InventoryBalance.variant_id == variant_id
            )
            .order_by(InventoryBalance.id.desc())
        )

        return list(result.scalars().all())