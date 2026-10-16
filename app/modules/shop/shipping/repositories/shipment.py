
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.shop.shipping.models.shipment import Shipment


class ShipmentRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_order_id(
        self,
        order_id: int,
        *,
        for_update: bool = False,
    ) -> Shipment | None:
        statement = select(Shipment).where(
            Shipment.order_id == order_id
        )

        if for_update:
            statement = statement.with_for_update()

        return self.db.scalar(statement)


    def get_by_awb(self, awb_code: str, for_update: bool = False):
        statement = select(Shipment).where(
            Shipment.awb_code == awb_code
        )

        if for_update:
            statement = statement.with_for_update()

        return self.db.scalar(statement)


    def create(self, shipment: Shipment) -> Shipment:
        self.db.add(shipment)
        self.db.flush()
        return shipment

    def save(self) -> None:
        self.db.flush()
