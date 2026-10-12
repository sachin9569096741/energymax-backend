
from __future__ import annotations

from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.modules.shop.inventory.constants.enums import (
    InventoryMovementType,
    InventoryReservationStatus,
)
from app.modules.shop.inventory.models.inventory_reservation import (
    InventoryReservation,
)
from app.modules.shop.inventory.repositories.inventory_balance import (
    InventoryBalanceRepository,
)
from app.modules.shop.inventory.repositories.inventory_movement import (
    InventoryMovementRepository,
)
from app.modules.shop.inventory.repositories.inventory_reservation import (
    InventoryReservationRepository,
)


class InventoryReservationService:
    def __init__(self, db: Session):
        self.db = db
        self.reservation_repository = InventoryReservationRepository(db)
        self.balance_repository = InventoryBalanceRepository(db)
        self.movement_repository = InventoryMovementRepository(db)

    # ================================================================
    # CREATE RESERVATION
    # ================================================================

    def create(
        self,
        *,
        warehouse_id: int,
        variant_id: int,
        quantity: Decimal,
        reference_type: str,
        reference_id: str,
        idempotency_key: str | None = None,
        expires_at=None,
    ) -> InventoryReservation:
        quantity = Decimal(str(quantity))

        if quantity <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reservation quantity must be greater than zero.",
            )

        reference_type = reference_type.strip()
        reference_id = reference_id.strip()

        if not reference_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reference type is required.",
            )

        if not reference_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reference ID is required.",
            )

        # IDEMPOTENCY CHECK
        if idempotency_key:
            idempotency_key = idempotency_key.strip()

            existing_reservation = (
                self.reservation_repository.get_by_idempotency_key(
                    idempotency_key=idempotency_key
                )
            )

            if existing_reservation is not None:
                if existing_reservation.warehouse_id != warehouse_id:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=(
                            "Idempotency key was already used "
                            "with a different warehouse."
                        ),
                    )

                if existing_reservation.variant_id != variant_id:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=(
                            "Idempotency key was already used "
                            "with a different variant."
                        ),
                    )

                if Decimal(str(existing_reservation.quantity)) != quantity:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=(
                            "Idempotency key was already used "
                            "with a different quantity."
                        ),
                    )

                if existing_reservation.reference_type != reference_type:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=(
                            "Idempotency key was already used "
                            "with a different reference type."
                        ),
                    )

                if existing_reservation.reference_id != reference_id:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=(
                            "Idempotency key was already used "
                            "with a different reference ID."
                        ),
                    )

                return existing_reservation

        # EXPIRY DISABLED: reservations do not expire automatically.
        expires_at = None

        # LOCK INVENTORY BALANCE
        balance = self.balance_repository.get_for_update(
            warehouse_id=warehouse_id,
            variant_id=variant_id,
        )

        if balance is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Inventory balance not found.",
            )

        # CALCULATE AVAILABLE STOCK
        on_hand = Decimal(str(balance.on_hand))
        reserved = Decimal(str(balance.reserved))
        damaged = Decimal(str(balance.damaged))

        available = on_hand - reserved - damaged

        if available < quantity:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Insufficient available stock. "
                    f"Available: {available}, "
                    f"Requested: {quantity}."
                ),
            )

        # INCREASE RESERVED STOCK
        balance.reserved = reserved + quantity
        self.db.flush()

        # CREATE RESERVATION
        reservation = self.reservation_repository.create(
            warehouse_id=warehouse_id,
            variant_id=variant_id,
            quantity=quantity,
            status=InventoryReservationStatus.ACTIVE.value,
            reference_type=reference_type,
            reference_id=reference_id,
            idempotency_key=idempotency_key,
            expires_at=None,
        )

        # CREATE AUDIT MOVEMENT
        self.movement_repository.create(
            warehouse_id=warehouse_id,
            variant_id=variant_id,
            movement_type=InventoryMovementType.RESERVATION.value,
            quantity=quantity,
            before_quantity=on_hand,
            after_quantity=on_hand,
            reference_type=reference_type,
            reference_id=reference_id,
            note=f"Reserved {quantity} units",
        )

        self.db.flush()
        return reservation

    # ================================================================
    # RELEASE RESERVATION
    # ================================================================

    def release(
        self,
        *,
        reservation_id: int,
    ) -> InventoryReservation:
        reservation = self.reservation_repository.get_for_update(
            reservation_id
        )

        if reservation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reservation not found.",
            )

        if reservation.status != InventoryReservationStatus.ACTIVE.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only active reservations can be released.",
            )

        balance = self.balance_repository.get_for_update(
            warehouse_id=reservation.warehouse_id,
            variant_id=reservation.variant_id,
        )

        if balance is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Inventory balance not found.",
            )

        quantity = Decimal(str(reservation.quantity))
        reserved = Decimal(str(balance.reserved))

        if reserved < quantity:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Reserved stock is lower than "
                    "reservation quantity."
                ),
            )

        on_hand = Decimal(str(balance.on_hand))

        # Release reserved stock; do not deduct on-hand stock.
        balance.reserved = reserved - quantity
        reservation.status = InventoryReservationStatus.RELEASED.value

        self.db.flush()

        # RELEASE AUDIT MOVEMENT
        self.movement_repository.create(
            warehouse_id=reservation.warehouse_id,
            variant_id=reservation.variant_id,
            movement_type=InventoryMovementType.RELEASE.value,
            quantity=quantity,
            before_quantity=on_hand,
            after_quantity=on_hand,
            reference_type=reservation.reference_type,
            reference_id=reservation.reference_id,
            note=f"Released {quantity} units",
        )

        self.db.flush()
        return reservation

    # ================================================================
    # CONFIRM RESERVATION
    # ================================================================

    def confirm(
        self,
        *,
        reservation_id: int,
    ) -> InventoryReservation:
        reservation = self.reservation_repository.get_for_update(
            reservation_id
        )

        if reservation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reservation not found.",
            )

        if reservation.status == InventoryReservationStatus.CONFIRMED.value:
            return reservation

        if reservation.status != InventoryReservationStatus.ACTIVE.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only active reservations can be confirmed.",
            )

        # Expiry validation intentionally removed.

        # LOCK BALANCE
        balance = self.balance_repository.get_for_update(
            warehouse_id=reservation.warehouse_id,
            variant_id=reservation.variant_id,
        )

        if balance is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Inventory balance not found.",
            )

        quantity = Decimal(str(reservation.quantity))
        on_hand = Decimal(str(balance.on_hand))
        reserved = Decimal(str(balance.reserved))
        damaged = Decimal(str(balance.damaged))

        if reserved < quantity:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Reserved stock is lower than "
                    "reservation quantity."
                ),
            )

        # CHECK ACTUAL DEDUCTIBLE STOCK
        available_for_deduction = (
            on_hand - reserved - damaged + quantity
        )

        if available_for_deduction < quantity:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Insufficient stock for confirmation. "
                    f"Available: {available_for_deduction}, "
                    f"Required: {quantity}."
                ),
            )

        # DEDUCT STOCK
        balance.on_hand = on_hand - quantity
        balance.reserved = reserved - quantity
        reservation.status = InventoryReservationStatus.CONFIRMED.value

        self.db.flush()

        # SALE MOVEMENT
        self.movement_repository.create(
            warehouse_id=reservation.warehouse_id,
            variant_id=reservation.variant_id,
            movement_type=InventoryMovementType.SALE.value,
            quantity=quantity,
            before_quantity=on_hand,
            after_quantity=balance.on_hand,
            reference_type=reservation.reference_type,
            reference_id=reservation.reference_id,
            note=(
                f"Reservation confirmed and "
                f"{quantity} units deducted"
            ),
        )

        self.db.flush()
        return reservation

    # ================================================================
    # EXPIRE RESERVATIONS
    # ================================================================

    def expire_reservations(self) -> int:
        """
        Automatic expiry is disabled.

        Retained for compatibility with existing scheduled jobs.
        This method must not release stock or change reservation status.
        """
        return 0
