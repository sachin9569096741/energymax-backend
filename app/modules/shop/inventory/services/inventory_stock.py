from __future__ import annotations

from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.modules.shop.inventory.constants.enums import (
    InventoryMovementType,
)
from app.modules.shop.inventory.models.inventory_balance import (
    InventoryBalance,
)
from app.modules.shop.inventory.models.inventory_movement import (
    InventoryMovement,
)
from app.modules.shop.inventory.repositories.inventory_balance import (
    InventoryBalanceRepository,
)
from app.modules.shop.inventory.repositories.inventory_movement import (
    InventoryMovementRepository,
)


class InventoryStockService:
    def __init__(self, db: Session):
        self.db = db

        self.balance_repository = InventoryBalanceRepository(db)
        self.movement_repository = InventoryMovementRepository(db)

    # ------------------------------------------------------------------
    # STOCK IN
    # ------------------------------------------------------------------

    def stock_in(
        self,
        *,
        warehouse_id: int,
        variant_id: int,
        quantity: Decimal,
        movement_type: InventoryMovementType = InventoryMovementType.STOCK_IN,
        reference_type: str | None = None,
        reference_id: str | None = None,
        idempotency_key: str | None = None,
        note: str | None = None,
    ) -> tuple[InventoryBalance, InventoryMovement]:

        self._validate_quantity(quantity)

        # --------------------------------------------------------------
        # IDEMPOTENCY CHECK
        # --------------------------------------------------------------

        if idempotency_key:
            existing_movement = (
                self.movement_repository.get_by_idempotency_key(
                    idempotency_key
                )
            )

            if existing_movement:

                self._validate_existing_operation(
                    existing_movement=existing_movement,
                    warehouse_id=warehouse_id,
                    variant_id=variant_id,
                    movement_type=movement_type,
                    quantity=quantity,
                    reference_type=reference_type,
                    reference_id=reference_id,
                )

                balance = self.balance_repository.get_for_update(
                    warehouse_id=existing_movement.warehouse_id,
                    variant_id=existing_movement.variant_id,
                )

                if not balance:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=(
                            "Idempotent operation exists, "
                            "but its inventory balance could not be found"
                        ),
                    )

                return balance, existing_movement

        # --------------------------------------------------------------
        # LOCK INVENTORY BALANCE
        # --------------------------------------------------------------

        balance = self.balance_repository.get_for_update(
            warehouse_id=warehouse_id,
            variant_id=variant_id,
        )

        if not balance:
            balance = self.balance_repository.create(
                warehouse_id=warehouse_id,
                variant_id=variant_id,
                on_hand=Decimal("0"),
                reserved=Decimal("0"),
                damaged=Decimal("0"),
                incoming=Decimal("0"),
                reorder_level=Decimal("0"),
                reorder_quantity=Decimal("0"),
                safety_stock=Decimal("0"),
            )

        before_quantity = Decimal(balance.on_hand)

        after_quantity = before_quantity + quantity

        # --------------------------------------------------------------
        # UPDATE BALANCE
        # --------------------------------------------------------------

        self.balance_repository.update(
            balance,
            on_hand=after_quantity,
        )

        # --------------------------------------------------------------
        # CREATE MOVEMENT
        # --------------------------------------------------------------

        movement = self.movement_repository.create(
            warehouse_id=warehouse_id,
            variant_id=variant_id,
            movement_type=movement_type.value,
            quantity=quantity,
            before_quantity=before_quantity,
            after_quantity=after_quantity,
            reference_type=reference_type,
            reference_id=reference_id,
            idempotency_key=idempotency_key,
            note=note,
        )

        return balance, movement

    # ------------------------------------------------------------------
    # STOCK OUT
    # ------------------------------------------------------------------

    def stock_out(
        self,
        *,
        warehouse_id: int,
        variant_id: int,
        quantity: Decimal,
        movement_type: InventoryMovementType = InventoryMovementType.STOCK_OUT,
        reference_type: str | None = None,
        reference_id: str | None = None,
        idempotency_key: str | None = None,
        note: str | None = None,
    ) -> tuple[InventoryBalance, InventoryMovement]:

        self._validate_quantity(quantity)

        # --------------------------------------------------------------
        # IDEMPOTENCY CHECK
        # --------------------------------------------------------------

        if idempotency_key:
            existing_movement = (
                self.movement_repository.get_by_idempotency_key(
                    idempotency_key
                )
            )

            if existing_movement:

                self._validate_existing_operation(
                    existing_movement=existing_movement,
                    warehouse_id=warehouse_id,
                    variant_id=variant_id,
                    movement_type=movement_type,
                    quantity=quantity,
                    reference_type=reference_type,
                    reference_id=reference_id,
                )

                balance = self.balance_repository.get_for_update(
                    warehouse_id=existing_movement.warehouse_id,
                    variant_id=existing_movement.variant_id,
                )

                if not balance:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=(
                            "Idempotent operation exists, "
                            "but its inventory balance could not be found"
                        ),
                    )

                return balance, existing_movement

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
                detail=(
                    "Inventory balance not found "
                    "for this warehouse and variant"
                ),
            )

        # --------------------------------------------------------------
        # AVAILABLE STOCK
        # --------------------------------------------------------------

        available = (
            Decimal(balance.on_hand)
            - Decimal(balance.reserved)
            - Decimal(balance.damaged)
        )

        if available < quantity:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Insufficient available stock. "
                    f"Available: {available}, "
                    f"Requested: {quantity}"
                ),
            )

        before_quantity = Decimal(balance.on_hand)

        after_quantity = before_quantity - quantity

        if after_quantity < 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Stock cannot become negative",
            )

        # --------------------------------------------------------------
        # UPDATE BALANCE
        # --------------------------------------------------------------

        self.balance_repository.update(
            balance,
            on_hand=after_quantity,
        )

        # --------------------------------------------------------------
        # CREATE MOVEMENT
        # --------------------------------------------------------------

        movement = self.movement_repository.create(
            warehouse_id=warehouse_id,
            variant_id=variant_id,
            movement_type=movement_type.value,
            quantity=quantity,
            before_quantity=before_quantity,
            after_quantity=after_quantity,
            reference_type=reference_type,
            reference_id=reference_id,
            idempotency_key=idempotency_key,
            note=note,
        )

        return balance, movement

    # ------------------------------------------------------------------
    # IDEMPOTENCY VALIDATION
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_existing_operation(
        *,
        existing_movement: InventoryMovement,
        warehouse_id: int,
        variant_id: int,
        movement_type: InventoryMovementType,
        quantity: Decimal,
        reference_type: str | None,
        reference_id: str | None,
    ) -> None:

        if existing_movement.warehouse_id != warehouse_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Idempotency key was already used "
                    "for a different warehouse"
                ),
            )

        if existing_movement.variant_id != variant_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Idempotency key was already used "
                    "for a different product variant"
                ),
            )

        if existing_movement.movement_type != movement_type.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Idempotency key was already used "
                    "for a different inventory operation"
                ),
            )

        if Decimal(existing_movement.quantity) != Decimal(quantity):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Idempotency key was already used "
                    "with a different quantity"
                ),
            )

        if existing_movement.reference_type != reference_type:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Idempotency key was already used "
                    "with a different reference type"
                ),
            )

        if existing_movement.reference_id != reference_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Idempotency key was already used "
                    "with a different reference"
                ),
            )

    # ------------------------------------------------------------------
    # VALIDATION
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_quantity(
        quantity: Decimal,
    ) -> None:

        if quantity <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Quantity must be greater than zero",
            )