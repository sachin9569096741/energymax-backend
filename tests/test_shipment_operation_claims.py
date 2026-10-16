from types import SimpleNamespace

import pytest

from app.modules.shop.shipping.services.shipment import ShipmentService


FIELDS = {
    "awb": "awb_operation_status",
    "pickup": "pickup_operation_status",
    "label": "label_operation_status",
    "manifest": "manifest_operation_status",
}


class FakeDB:
    """Small test double simulating the conditional database claim."""

    def __init__(self, shipment=None, operation_field=None):
        self.shipment = shipment
        self.operation_field = operation_field
        self.commits = 0
        self.refreshes = 0
        self.rollbacks = 0
        self.scalar_calls = 0

    def scalar(self, statement):
        self.scalar_calls += 1
        field = self.operation_field

        if (
            self.shipment is None
            or field is None
            or getattr(self.shipment, field) != "idle"
        ):
            return None

        setattr(self.shipment, field, "in_progress")
        return self.shipment.id

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def refresh(self, obj):
        self.refreshes += 1


def make_shipment():
    return SimpleNamespace(
        id=123,
        **{name: "idle" for name in FIELDS.values()},
    )


@pytest.mark.parametrize("operation,field", FIELDS.items())
def test_claim_moves_idle_operation_to_in_progress(operation, field):
    shipment = make_shipment()
    db = FakeDB(shipment, field)
    service = ShipmentService(db=db, shiprocket_client=object())

    service._claim_operation(shipment, operation)

    assert getattr(shipment, field) == "in_progress"
    assert db.scalar_calls == 1
    assert db.commits == 1
    assert db.refreshes == 1
    assert db.rollbacks == 0


@pytest.mark.parametrize("operation,field", FIELDS.items())
@pytest.mark.parametrize("state", ["in_progress", "unknown", "succeeded"])
def test_claim_rejects_non_idle_operation(operation, field, state):
    shipment = make_shipment()
    setattr(shipment, field, state)
    db = FakeDB(shipment, field)
    service = ShipmentService(db=db, shiprocket_client=object())

    with pytest.raises(ValueError, match="cannot be claimed"):
        service._claim_operation(shipment, operation)

    assert getattr(shipment, field) == state
    assert db.scalar_calls == 1
    assert db.commits == 0
    assert db.refreshes == 0
    assert db.rollbacks == 1


def test_claim_rejects_unsupported_operation():
    shipment = make_shipment()
    db = FakeDB(shipment)
    service = ShipmentService(db=db, shiprocket_client=object())

    with pytest.raises(ValueError, match="Unsupported"):
        service._claim_operation(shipment, "unknown_operation")

    assert db.scalar_calls == 0
    assert db.commits == 0
    assert db.refreshes == 0
    assert db.rollbacks == 0
