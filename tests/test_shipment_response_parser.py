import pytest

from app.modules.shop.shipping.services.shipment import (
    _find_response_value,
)


@pytest.mark.parametrize(
    ("payload", "key", "expected"),
    [
        (
            {"response": {"data": {"awb_code": "AWB123"}}},
            "awb_code",
            "AWB123",
        ),
        (
            {"data": {"courier_name": "Test Courier"}},
            "courier_name",
            "Test Courier",
        ),
        (
            {"response": {"data": {"pickup_token_number": "PICK123"}}},
            "pickup_token_number",
            "PICK123",
        ),
        (
            {"data": {"label_created": 1, "label_url": "https://example.com/label.pdf"}},
            "label_url",
            "https://example.com/label.pdf",
        ),
        (
            {"response": {"manifest_url": "https://example.com/manifest.pdf"}},
            "manifest_url",
            "https://example.com/manifest.pdf",
        ),
        (
            {"data": [{"awb_code": "AWB456"}]},
            "awb_code",
            "AWB456",
        ),
        (
            {"data": {"awb_code": None}},
            "awb_code",
            None,
        ),
        (
            {"data": {"awb_code": "AWB789"}},
            "missing_field",
            None,
        ),
    ],
)
def test_find_response_value(payload, key, expected):
    assert _find_response_value(payload, key) == expected
