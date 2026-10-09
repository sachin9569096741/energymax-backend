from __future__ import annotations

from typing import Optional
from app.modules.shop.catalog.models.product_variant import (
    ProductVariant,
)
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.modules.shop.inventory.models.inventory_movement import (
    InventoryMovement,
)


class InventoryMovementRepository:
    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # GET BY ID
    # ------------------------------------------------------------------

    def get_by_id(
        self,
        movement_id: int,
    ) -> Optional[InventoryMovement]:

        result = self.db.execute(
            select(InventoryMovement).where(
                InventoryMovement.id == movement_id
            )
        )

        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # CREATE MOVEMENT
    # ------------------------------------------------------------------

    def create(
        self,
        *,
        warehouse_id: int,
        variant_id: int,
        movement_type: str,
        quantity,
        before_quantity,
        after_quantity,
        reference_type: str | None = None,
        reference_id: str | None = None,
        idempotency_key: str | None = None,
        note: str | None = None,
    ) -> InventoryMovement:

        movement = InventoryMovement(
            warehouse_id=warehouse_id,
            variant_id=variant_id,
            movement_type=movement_type,
            quantity=quantity,
            before_quantity=before_quantity,
            after_quantity=after_quantity,
            reference_type=reference_type,
            reference_id=reference_id,
            idempotency_key=idempotency_key,
            note=note,
        )

        self.db.add(movement)
        self.db.flush()
        self.db.refresh(movement)

        return movement

    # ------------------------------------------------------------------
    # LIST MOVEMENTS
    # ------------------------------------------------------------------

    def list(
        self,
        *,
        warehouse_id: int | None = None,
        variant_id: int | None = None,
        movement_type: str | None = None,
        reference_type: str | None = None,
        reference_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[InventoryMovement]:

        query = select(InventoryMovement)

        if warehouse_id is not None:
            query = query.where(
                InventoryMovement.warehouse_id == warehouse_id
            )

        if variant_id is not None:
            query = query.where(
                InventoryMovement.variant_id == variant_id
            )

        if movement_type is not None:
            query = query.where(
                InventoryMovement.movement_type == movement_type
            )

        if reference_type is not None:
            query = query.where(
                InventoryMovement.reference_type == reference_type
            )

        if reference_id is not None:
            query = query.where(
                InventoryMovement.reference_id == reference_id
            )

        query = (
            query
            .order_by(
                InventoryMovement.created_at.desc()
            )
            .offset(offset)
            .limit(limit)
        )

        result = self.db.execute(query)

        return list(result.scalars().all())


        # ------------------------------------------------------------------
    # LIST MOVEMENTS WITH DETAILS
    # ------------------------------------------------------------------

    def list_detailed(
        self,
        *,
        warehouse_id: int | None = None,
        variant_id: int | None = None,
        movement_type: str | None = None,
        reference_type: str | None = None,
        reference_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[InventoryMovement]:

        query = (
            select(InventoryMovement)
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
        )

        if warehouse_id is not None:
            query = query.where(
                InventoryMovement.warehouse_id == warehouse_id
            )

        if variant_id is not None:
            query = query.where(
                InventoryMovement.variant_id == variant_id
            )

        if movement_type is not None:
            query = query.where(
                InventoryMovement.movement_type == movement_type
            )

        if reference_type is not None:
            query = query.where(
                InventoryMovement.reference_type == reference_type
            )

        if reference_id is not None:
            query = query.where(
                InventoryMovement.reference_id == reference_id
            )

        query = (
            query
            .order_by(
                InventoryMovement.created_at.desc(),
                InventoryMovement.id.desc(),
            )
            .offset(offset)
            .limit(limit)
        )

        result = self.db.execute(query)

        return list(
            result.scalars().unique().all()
        )
    # ------------------------------------------------------------------
    # GET BY REFERENCE
    # ------------------------------------------------------------------

    def get_by_reference(
        self,
        *,
        reference_type: str,
        reference_id: str,
    ) -> list[InventoryMovement]:

        result = self.db.execute(
            select(InventoryMovement)
            .where(
                InventoryMovement.reference_type == reference_type,
                InventoryMovement.reference_id == reference_id,
            )
            .order_by(
                InventoryMovement.created_at.asc()
            )
        )

        return list(result.scalars().all())


        # ------------------------------------------------------------------
    # GET BY IDEMPOTENCY KEY
    # ------------------------------------------------------------------

    def get_by_idempotency_key(
        self,
        idempotency_key: str,
    ) -> Optional[InventoryMovement]:

        result = self.db.execute(
            select(InventoryMovement).where(
                InventoryMovement.idempotency_key
                == idempotency_key
            )
        )

        return result.scalar_one_or_none()
    # ------------------------------------------------------------------
    # GET LATEST MOVEMENT
    # ------------------------------------------------------------------

    def get_latest(
        self,
        *,
        warehouse_id: int,
        variant_id: int,
    ) -> Optional[InventoryMovement]:

        result = self.db.execute(
            select(InventoryMovement)
            .where(
                InventoryMovement.warehouse_id == warehouse_id,
                InventoryMovement.variant_id == variant_id,
            )
            .order_by(
                InventoryMovement.created_at.desc(),
                InventoryMovement.id.desc(),
            )
            .limit(1)
        )

        return result.scalar_one_or_none()