from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.shop.inventory.models.warehouse import Warehouse


class WarehouseRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, warehouse_id: int) -> Optional[Warehouse]:
        result = self.db.execute(
            select(Warehouse).where(Warehouse.id == warehouse_id)
        )
        return result.scalar_one_or_none()

    def get_by_public_id(
        self,
        public_id: str,
    ) -> Optional[Warehouse]:
        result = self.db.execute(
            select(Warehouse).where(Warehouse.public_id == public_id)
        )
        return result.scalar_one_or_none()

    def get_by_code(
        self,
        code: str,
    ) -> Optional[Warehouse]:
        result = self.db.execute(
            select(Warehouse).where(Warehouse.code == code)
        )
        return result.scalar_one_or_none()

    def list(
        self,
        active_only: bool = False,
    ) -> list[Warehouse]:

        query = select(Warehouse).order_by(
            Warehouse.id.desc()
        )

        if active_only:
            query = query.where(
                Warehouse.is_active.is_(True)
            )

        result = self.db.execute(query)

        return list(result.scalars().all())

    def create(
        self,
        *,
        name: str,
        code: str,
        address: Optional[str] = None,
    ) -> Warehouse:

        warehouse = Warehouse(
            name=name,
            code=code,
            address=address,
        )

        self.db.add(warehouse)
        self.db.flush()
        self.db.refresh(warehouse)

        return warehouse

    def update(
        self,
        warehouse: Warehouse,
        *,
        name: Optional[str] = None,
        code: Optional[str] = None,
        address: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> Warehouse:

        if name is not None:
            warehouse.name = name

        if code is not None:
            warehouse.code = code

        if address is not None:
            warehouse.address = address

        if is_active is not None:
            warehouse.is_active = is_active

        self.db.flush()
        self.db.refresh(warehouse)

        return warehouse