from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.shop.inventory.models.stock_adjustment import (
    StockAdjustment,
)


class StockAdjustmentRepository:
    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # GET BY ID
    # ------------------------------------------------------------------

    def get_by_id(
        self,
        adjustment_id: int,
    ) -> Optional[StockAdjustment]:

        result = self.db.execute(
            select(StockAdjustment).where(
                StockAdjustment.id == adjustment_id
            )
        )

        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # GET BY PUBLIC ID
    # ------------------------------------------------------------------

    def get_by_public_id(
        self,
        public_id: str,
    ) -> Optional[StockAdjustment]:

        result = self.db.execute(
            select(StockAdjustment).where(
                StockAdjustment.public_id == public_id
            )
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
        adjustment_type: str,
        quantity,
        reason: str,
        before_quantity,
        after_quantity,
                idempotency_key: str | None = None,
    ) -> StockAdjustment:

        adjustment = StockAdjustment(
            warehouse_id=warehouse_id,
            variant_id=variant_id,
            adjustment_type=adjustment_type,
            quantity=quantity,
            reason=reason,
            before_quantity=before_quantity,
            after_quantity=after_quantity,
            idempotency_key=idempotency_key,
        )

        self.db.add(adjustment)
        self.db.flush()
        self.db.refresh(adjustment)

        return adjustment

    # ------------------------------------------------------------------
    # LIST
    # ------------------------------------------------------------------

    def list(
        self,
        *,
        warehouse_id: int | None = None,
        variant_id: int | None = None,
        adjustment_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[StockAdjustment]:

        query = select(StockAdjustment)

        if warehouse_id is not None:
            query = query.where(
                StockAdjustment.warehouse_id == warehouse_id
            )

        if variant_id is not None:
            query = query.where(
                StockAdjustment.variant_id == variant_id
            )

        if adjustment_type is not None:
            query = query.where(
                StockAdjustment.adjustment_type
                == adjustment_type
            )

        query = (
            query
            .order_by(
                StockAdjustment.created_at.desc(),
                StockAdjustment.id.desc(),
            )
            .offset(offset)
            .limit(limit)
        )

        result = self.db.execute(query)

        return list(result.scalars().all())


        # ------------------------------------------------------------------
    # GET BY IDEMPOTENCY KEY
    # ------------------------------------------------------------------

    def get_by_idempotency_key(
        self,
        idempotency_key: str,
    ) -> Optional[StockAdjustment]:

        result = self.db.execute(
            select(StockAdjustment).where(
                StockAdjustment.idempotency_key
                == idempotency_key
            )
        )

        return result.scalar_one_or_none()