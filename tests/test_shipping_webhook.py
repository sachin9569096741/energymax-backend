

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.modules.shop.shipping.routes.webhook import (
    _advance_order_status,
    _get_tracking_status,
)


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ({"shipment_status_id": 6}, ("SHIPPED", "shipped")),
        ({"shipment_status_id": 42}, ("PICKED UP", "shipped")),
        ({"shipment_status_id": 18}, ("IN TRANSIT", "shipped")),
        ({"shipment_status_id": 17}, ("OUT FOR DELIVERY", "out_for_delivery")),
        ({"shipment_status_id": 7}, ("DELIVERED", "delivered")),
        ({"shipment_status": "DELIVERED"}, ("DELIVERED", "delivered")),
        ({}, ("UNKNOWN", None)),
    ],
)
def test_get_tracking_status(payload, expected):
    assert _get_tracking_status(payload) == expected


class FakeOrderService:
    def __init__(self, db):
        pass

    def update_order_status(
        self, order, new_status, note=None, changed_by=None
    ):
        allowed = {
            "packed": {"shipped"},
            "shipped": {"out_for_delivery"},
            "out_for_delivery": {"delivered"},
        }
        if new_status not in allowed.get(order.status, set()):
            raise ValueError(
                f"Invalid transition: {order.status} -> {new_status}"
            )
        order.status = new_status


@pytest.mark.parametrize(
    ("initial", "target", "expected_changed", "expected_final"),
    [
        ("packed", "shipped", True, "shipped"),
        ("shipped", "out_for_delivery", True, "out_for_delivery"),
        ("out_for_delivery", "delivered", True, "delivered"),
        ("packed", "delivered", True, "delivered"),
        ("delivered", "shipped", False, "delivered"),
        ("cancelled", "shipped", False, "cancelled"),
        ("refunded", "delivered", False, "refunded"),
        ("returned", "delivered", False, "returned"),
    ],
)
def test_advance_order_status(
    initial, target, expected_changed, expected_final
):
    order = SimpleNamespace(status=initial)

    with patch(
        "app.modules.shop.shipping.routes.webhook.OrderService",
        FakeOrderService,
    ):
        changed = _advance_order_status(order, target, db=None)

    assert changed is expected_changed
    assert order.status == expected_final
