from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.shop.inventory.models.inventory_reservation import (
    InventoryReservation,
)
from app.modules.shop.inventory.constants.enums import (
    InventoryReservationStatus,
)


class InventoryReservationRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(
        self,
        reservation_id: int,
    ) -> Optional[InventoryReservation]:
        result = self.db.execute(
            select(InventoryReservation).where(
                InventoryReservation.id == reservation_id
            )
        )

        return result.scalar_one_or_none()

    def get_for_update(
        self,
        reservation_id: int,
    ) -> Optional[InventoryReservation]:
        result = self.db.execute(
            select(InventoryReservation)
            .where(
                InventoryReservation.id == reservation_id
            )
            .with_for_update()
        )

        return result.scalar_one_or_none()

    def get_by_reference(
        self,
        reference_type: str,
        reference_id: str,
    ) -> list[InventoryReservation]:

        result = self.db.execute(
            select(InventoryReservation)
            .where(
                InventoryReservation.reference_type
                == reference_type,
                InventoryReservation.reference_id
                == reference_id,
            )
            .order_by(
                InventoryReservation.created_at.desc()
            )
        )

        return list(result.scalars().all())


    
    def create(
        self,
        *,
        warehouse_id: int,
        variant_id: int,
        quantity,
        status: str,
        reference_type: str,
        reference_id: str,
                idempotency_key: str | None = None,
        expires_at: datetime | None = None,
    ) -> InventoryReservation:

        reservation = InventoryReservation(
            warehouse_id=warehouse_id,
            variant_id=variant_id,
            quantity=quantity,
            status=status,
            reference_type=reference_type,
            reference_id=reference_id,
            idempotency_key=idempotency_key,
            expires_at=expires_at,
        )

        self.db.add(reservation)
        self.db.flush()
        self.db.refresh(reservation)

        return reservation

    def list(
        self,
        *,
        warehouse_id: int | None = None,
        variant_id: int | None = None,
        status: str | None = None,
        reference_type: str | None = None,
        reference_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[InventoryReservation]:

        query = select(InventoryReservation)

        if warehouse_id is not None:
            query = query.where(
                InventoryReservation.warehouse_id
                == warehouse_id
            )

        if variant_id is not None:
            query = query.where(
                InventoryReservation.variant_id
                == variant_id
            )

        if status is not None:
            query = query.where(
                InventoryReservation.status
                == status
            )

        if reference_type is not None:
            query = query.where(
                InventoryReservation.reference_type
                == reference_type
            )

        if reference_id is not None:
            query = query.where(
                InventoryReservation.reference_id
                == reference_id
            )

        query = (
            query
            .order_by(
                InventoryReservation.created_at.desc()
            )
            .offset(offset)
            .limit(limit)
        )

        result = self.db.execute(query)

        return list(result.scalars().all())


    def get_expired_active(
        self,
        *,
        now: datetime,
    ) -> list[InventoryReservation]:

        result = self.db.execute(
            select(InventoryReservation)
            .where(
                InventoryReservation.status
                == InventoryReservationStatus.ACTIVE.value,
                InventoryReservation.expires_at.is_not(None),
                InventoryReservation.expires_at <= now,
            )
            .with_for_update()
        )

        return list(result.scalars().all())

        # ------------------------------------------------------------------
    # GET BY IDEMPOTENCY KEY
    # ------------------------------------------------------------------

    def get_by_idempotency_key(
        self,
        idempotency_key: str,
    ) -> Optional[InventoryReservation]:

        result = self.db.execute(
            select(InventoryReservation).where(
                InventoryReservation.idempotency_key
                == idempotency_key
            )
        )

        return result.scalar_one_or_none()