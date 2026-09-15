from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.admin.auth.models.role import Role


class RoleRepository:

    def __init__(self, db: Session):
        self.db = db

    # ---------------------------------------------------------
    # GET BY ID
    # ---------------------------------------------------------

    def get_by_id(
        self,
        role_id: int,
    ) -> Role | None:

        statement = select(Role).where(
            Role.id == role_id
        )

        return self.db.scalar(statement)

    # ---------------------------------------------------------
    # GET BY PUBLIC ID
    # ---------------------------------------------------------

    def get_by_public_id(
        self,
        public_id: str,
    ) -> Role | None:

        statement = select(Role).where(
            Role.public_id == public_id
        )

        return self.db.scalar(statement)

    # ---------------------------------------------------------
    # GET BY NAME
    # ---------------------------------------------------------

    def get_by_name(
        self,
        name: str,
    ) -> Role | None:

        statement = select(Role).where(
            Role.name == name
        )

        return self.db.scalar(statement)

    # ---------------------------------------------------------
    # LIST
    # ---------------------------------------------------------

    def list(
        self,
        *,
        is_active: bool | None = None,
    ) -> list[Role]:

        statement = select(Role)

        if is_active is not None:
            statement = statement.where(
                Role.is_active == is_active
            )

        statement = statement.order_by(
            Role.name
        )

        return list(
            self.db.scalars(statement).all()
        )

    # ---------------------------------------------------------
    # CREATE
    # ---------------------------------------------------------

    def create(
        self,
        role: Role,
    ) -> Role:

        self.db.add(role)
        self.db.flush()
        self.db.refresh(role)

        return role

    # ---------------------------------------------------------
    # UPDATE
    # ---------------------------------------------------------

    def update(
        self,
        role: Role,
        data: dict,
    ) -> Role:

        for field, value in data.items():
            setattr(role, field, value)

        self.db.flush()
        self.db.refresh(role)

        return role

    # ---------------------------------------------------------
    # DELETE
    # ---------------------------------------------------------

    def delete(
        self,
        role: Role,
    ) -> None:

        self.db.delete(role)
        self.db.flush()