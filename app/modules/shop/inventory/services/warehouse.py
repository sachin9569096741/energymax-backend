from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.shop.inventory.models.warehouse import Warehouse
from app.modules.shop.inventory.repositories.warehouse import WarehouseRepository


class WarehouseService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = WarehouseRepository(db)

    def get_by_public_id(
        self,
        public_id: str,
    ) -> Warehouse:

        warehouse = self.repository.get_by_public_id(
            public_id
        )

        if not warehouse:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Warehouse not found",
            )

        return warehouse

    def list(
        self,
        active_only: bool = False,
    ) -> list[Warehouse]:

        return self.repository.list(
            active_only=active_only,
        )

    def create(
        self,
        *,
        name: str,
        code: str,
        address: str | None = None,
    ) -> Warehouse:

        name = name.strip()
        code = code.strip().upper()

        if not name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Warehouse name cannot be empty",
            )

        if not code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Warehouse code cannot be empty",
            )

        existing_code = self.repository.get_by_code(code)

        if existing_code:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Warehouse code already exists",
            )

        try:
            return self.repository.create(
                name=name,
                code=code,
                address=address,
            )

        except IntegrityError:
            self.db.rollback()

            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Warehouse already exists",
            )

    def update(
        self,
        public_id: str,
        *,
        name: str | None = None,
        code: str | None = None,
        address: str | None = None,
        is_active: bool | None = None,
    ) -> Warehouse:

        warehouse = self.get_by_public_id(public_id)

        normalized_name = (
            name.strip()
            if name is not None
            else None
        )

        normalized_code = (
            code.strip().upper()
            if code is not None
            else None
        )

        if normalized_name == "":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Warehouse name cannot be empty",
            )

        if normalized_code == "":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Warehouse code cannot be empty",
            )

        if (
            normalized_code is not None
            and normalized_code != warehouse.code
        ):
            existing_code = self.repository.get_by_code(
                normalized_code
            )

            if (
                existing_code
                and existing_code.id != warehouse.id
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Warehouse code already exists",
                )

        try:
            return self.repository.update(
                warehouse,
                name=normalized_name,
                code=normalized_code,
                address=address,
                is_active=is_active,
            )

        except IntegrityError:
            self.db.rollback()

            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Warehouse update conflicts with existing data",
            )