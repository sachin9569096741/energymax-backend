from __future__ import annotations

from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.modules.shop.inventory.constants.enums import (
    InventoryMovementType,
)
from app.modules.shop.inventory.models.inventory_movement import (
    InventoryMovement,
)
from app.modules.shop.inventory.repositories.inventory_movement import (
    InventoryMovementRepository,
)


class InventoryMovementService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = InventoryMovementRepository(db)

    # ------------------------------------------------------------------
    # CREATE MOVEMENT
    # ------------------------------------------------------------------

    def create(
        self,
        *,
        warehouse_id: int,
        variant_id: int,
        movement_type: InventoryMovementType,
        quantity: Decimal,
        before_quantity: Decimal,
        after_quantity: Decimal,
        reference_type: str | None = None,
        reference_id: str | None = None,
        note: str | None = None,
    ) -> InventoryMovement:

        if quantity <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Movement quantity must be greater than zero",
            )

        if before_quantity < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Before quantity cannot be negative",
            )

        if after_quantity < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="After quantity cannot be negative",
            )

        if reference_type is not None:
            reference_type = reference_type.strip()

        if reference_id is not None:
            reference_id = reference_id.strip()

        return self.repository.create(
            warehouse_id=warehouse_id,
            variant_id=variant_id,
            movement_type=movement_type.value,
            quantity=quantity,
            before_quantity=before_quantity,
            after_quantity=after_quantity,
            reference_type=reference_type,
            reference_id=reference_id,
            note=note,
        )

    # ------------------------------------------------------------------
    # GET MOVEMENT
    # ------------------------------------------------------------------

    def get_by_id(
        self,
        movement_id: int,
    ) -> InventoryMovement:

        movement = self.repository.get_by_id(
            movement_id
        )

        if not movement:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Inventory movement not found",
            )

        return movement

    # ------------------------------------------------------------------
    # LIST MOVEMENTS
    # ------------------------------------------------------------------

    def list(
        self,
        *,
        warehouse_id: int | None = None,
        variant_id: int | None = None,
        movement_type: InventoryMovementType | None = None,
        reference_type: str | None = None,
        reference_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[InventoryMovement]:

        if limit < 1 or limit > 500:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Limit must be between 1 and 500",
            )

        if offset < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Offset cannot be negative",
            )

        return self.repository.list(
            warehouse_id=warehouse_id,
            variant_id=variant_id,
            movement_type=(
                movement_type.value
                if movement_type is not None
                else None
            ),
            reference_type=reference_type,
            reference_id=reference_id,
            limit=limit,
            offset=offset,
        )


        # ------------------------------------------------------------------
    # LIST MOVEMENTS WITH DETAILS
    # ------------------------------------------------------------------

    def list_detailed(
        self,
        *,
        warehouse_id: int | None = None,
        variant_id: int | None = None,
        movement_type: InventoryMovementType | None = None,
        reference_type: str | None = None,
        reference_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[InventoryMovement]:

        if limit < 1 or limit > 500:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Limit must be between 1 and 500",
            )

        if offset < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Offset cannot be negative",
            )

        return self.repository.list_detailed(
            warehouse_id=warehouse_id,
            variant_id=variant_id,
            movement_type=(
                movement_type.value
                if movement_type is not None
                else None
            ),
            reference_type=reference_type,
            reference_id=reference_id,
            limit=limit,
            offset=offset,
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

        if not reference_type.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reference type cannot be empty",
            )

        if not reference_id.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reference ID cannot be empty",
            )

        return self.repository.get_by_reference(
            reference_type=reference_type.strip(),
            reference_id=reference_id.strip(),
        )

    # ------------------------------------------------------------------
    # GET LATEST
    # ------------------------------------------------------------------

    def get_latest(
        self,
        *,
        warehouse_id: int,
        variant_id: int,
    ) -> InventoryMovement | None:

        return self.repository.get_latest(
            warehouse_id=warehouse_id,
            variant_id=variant_id,
        )