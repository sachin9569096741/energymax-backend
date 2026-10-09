from __future__ import annotations

from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.modules.shop.inventory.constants.enums import (
    InventoryMovementType,
    StockAdjustmentType,
)

from app.modules.shop.inventory.models.stock_adjustment import (
    StockAdjustment,
)

from app.modules.shop.inventory.repositories.inventory_balance import (
    InventoryBalanceRepository,
)

from app.modules.shop.inventory.repositories.inventory_movement import (
    InventoryMovementRepository,
)

from app.modules.shop.inventory.repositories.stock_adjustment import (
    StockAdjustmentRepository,
)


class StockAdjustmentService:
    def __init__(self, db: Session):
        self.db = db

        self.adjustment_repository = (
            StockAdjustmentRepository(db)
        )

        self.balance_repository = (
            InventoryBalanceRepository(db)
        )

        self.movement_repository = (
            InventoryMovementRepository(db)
        )

    # ------------------------------------------------------------------
    # CREATE ADJUSTMENT
    # ------------------------------------------------------------------

    def create(
        self,
        *,
        warehouse_id: int,
        variant_id: int,
        adjustment_type: StockAdjustmentType,
        quantity: Decimal,
        reason: str,
        idempotency_key: str | None = None,
    ) -> StockAdjustment:

        # --------------------------------------------------------------
        # VALIDATE QUANTITY
        # --------------------------------------------------------------

        if quantity <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Adjustment quantity must be greater than zero",
            )

        # --------------------------------------------------------------
        # VALIDATE REASON
        # --------------------------------------------------------------

        reason = reason.strip()

        if not reason:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Adjustment reason is required",
            )

        # --------------------------------------------------------------
        # IDEMPOTENCY CHECK
        # --------------------------------------------------------------

        if idempotency_key:

            existing_adjustment = (
                self.adjustment_repository.get_by_idempotency_key(
                    idempotency_key=idempotency_key
                )
            )

            if existing_adjustment:

                # ------------------------------------------------------
                # SAME KEY + DIFFERENT WAREHOUSE
                # ------------------------------------------------------

                if existing_adjustment.warehouse_id != warehouse_id:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=(
                            "Idempotency key was already used "
                            "for a different warehouse"
                        ),
                    )

                # ------------------------------------------------------
                # SAME KEY + DIFFERENT VARIANT
                # ------------------------------------------------------

                if existing_adjustment.variant_id != variant_id:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=(
                            "Idempotency key was already used "
                            "for a different product variant"
                        ),
                    )

                # ------------------------------------------------------
                # SAME KEY + DIFFERENT ADJUSTMENT TYPE
                # ------------------------------------------------------

                if (
                    existing_adjustment.adjustment_type
                    != adjustment_type.value
                ):
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=(
                            "Idempotency key was already used "
                            "for a different adjustment type"
                        ),
                    )

                # ------------------------------------------------------
                # SAME KEY + DIFFERENT QUANTITY
                # ------------------------------------------------------

                if (
                    Decimal(existing_adjustment.quantity)
                    != Decimal(quantity)
                ):
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=(
                            "Idempotency key was already used "
                            "with a different quantity"
                        ),
                    )

                # ------------------------------------------------------
                # SAME KEY + DIFFERENT REASON
                # ------------------------------------------------------

                if existing_adjustment.reason != reason:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=(
                            "Idempotency key was already used "
                            "with a different reason"
                        ),
                    )

                # ------------------------------------------------------
                # IDEMPOTENT RETRY
                # ------------------------------------------------------

                return existing_adjustment

        # --------------------------------------------------------------
        # LOCK INVENTORY BALANCE
        # --------------------------------------------------------------

        balance = self.balance_repository.get_for_update(
            warehouse_id=warehouse_id,
            variant_id=variant_id,
        )

        if not balance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Inventory balance not found",
            )

        # --------------------------------------------------------------
        # CURRENT STOCK
        # --------------------------------------------------------------

        before_quantity = Decimal(balance.on_hand)

        # --------------------------------------------------------------
        # CALCULATE NEW STOCK
        # --------------------------------------------------------------

        if adjustment_type == StockAdjustmentType.INCREASE:

            after_quantity = (
                before_quantity + quantity
            )

        elif adjustment_type == StockAdjustmentType.DECREASE:

            after_quantity = (
                before_quantity - quantity
            )

            # Never allow negative stock
            if after_quantity < 0:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "Insufficient stock for adjustment. "
                        f"Current stock: {before_quantity}, "
                        f"Requested decrease: {quantity}"
                    ),
                )

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid stock adjustment type",
            )

        # --------------------------------------------------------------
        # UPDATE INVENTORY BALANCE
        # --------------------------------------------------------------

        balance.on_hand = after_quantity

        self.db.flush()

        # --------------------------------------------------------------
        # CREATE ADJUSTMENT RECORD
        # --------------------------------------------------------------

        adjustment = self.adjustment_repository.create(
            warehouse_id=warehouse_id,
            variant_id=variant_id,
            adjustment_type=adjustment_type.value,
            quantity=quantity,
            reason=reason,
            before_quantity=before_quantity,
            after_quantity=after_quantity,
            idempotency_key=idempotency_key,
        )

        # --------------------------------------------------------------
        # CREATE AUDIT MOVEMENT
        # --------------------------------------------------------------

        self.movement_repository.create(
            warehouse_id=warehouse_id,
            variant_id=variant_id,
            movement_type=InventoryMovementType.ADJUSTMENT.value,
            quantity=quantity,
            before_quantity=before_quantity,
            after_quantity=after_quantity,
            reference_type="STOCK_ADJUSTMENT",
            reference_id=adjustment.public_id,
            note=reason,
        )

        return adjustment

    # ------------------------------------------------------------------
    # GET BY ID
    # ------------------------------------------------------------------

    def get_by_id(
        self,
        adjustment_id: int,
    ) -> StockAdjustment:

        adjustment = (
            self.adjustment_repository.get_by_id(
                adjustment_id
            )
        )

        if not adjustment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Stock adjustment not found",
            )

        return adjustment

    # ------------------------------------------------------------------
    # GET BY PUBLIC ID
    # ------------------------------------------------------------------

    def get_by_public_id(
        self,
        public_id: str,
    ) -> StockAdjustment:

        adjustment = (
            self.adjustment_repository.get_by_public_id(
                public_id
            )
        )

        if not adjustment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Stock adjustment not found",
            )

        return adjustment

    # ------------------------------------------------------------------
    # LIST
    # ------------------------------------------------------------------

    def list(
        self,
        *,
        warehouse_id: int | None = None,
        variant_id: int | None = None,
        adjustment_type: StockAdjustmentType | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[StockAdjustment]:

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

        return self.adjustment_repository.list(
            warehouse_id=warehouse_id,
            variant_id=variant_id,
            adjustment_type=(
                adjustment_type.value
                if adjustment_type is not None
                else None
            ),
            limit=limit,
            offset=offset,
        )