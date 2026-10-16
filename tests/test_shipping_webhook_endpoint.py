from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.db.session import get_db


def test_webhook_rejects_invalid_api_key():
    fake_db = object()

    def override_db():
        yield fake_db

    app.dependency_overrides[get_db] = override_db

    try:
        with patch.object(
            settings, "shiprocket_webhook_secret", "local-test-secret"
        ):
            client = TestClient(app)
            response = client.post(
                "/api/v1/webhooks/logistics",
                headers={"x-api-key": "wrong-secret"},
                json={"awb": "TEST-AWB"},
            )

        assert response.status_code == 401
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_webhook_rejects_missing_awb():
    fake_db = object()

    def override_db():
        yield fake_db

    app.dependency_overrides[get_db] = override_db

    try:
        with patch.object(
            settings, "shiprocket_webhook_secret", "local-test-secret"
        ):
            client = TestClient(app)
            response = client.post(
                "/api/v1/webhooks/logistics",
                headers={"x-api-key": "local-test-secret"},
                json={"current_status": "IN TRANSIT"},
            )

        assert response.status_code == 400
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_webhook_duplicate_event_is_not_processed_again():
    fake_db = object()
    existing_event = SimpleNamespace(status="processed")

    class FakePaymentRepository:
        def __init__(self, db):
            pass

        def create_webhook_event_if_new(self, event):
            return None

        def get_webhook_event(self, *, provider, event_id):
            assert provider == "shiprocket"
            return existing_event

    def override_db():
        yield fake_db

    app.dependency_overrides[get_db] = override_db

    try:
        with (
            patch.object(
                settings, "shiprocket_webhook_secret", "local-test-secret"
            ),
            patch(
                "app.modules.shop.shipping.routes.webhook.PaymentRepository",
                FakePaymentRepository,
            ),
        ):
            client = TestClient(app)
            payload = {
                "awb": "TEST-AWB-DUPLICATE",
                "current_status": "IN TRANSIT",
                "current_status_id": 18,
                "shipment_status": "IN TRANSIT",
                "shipment_status_id": 18,
            }

            first = client.post(
                "/api/v1/webhooks/logistics",
                headers={"x-api-key": "local-test-secret"},
                json=payload,
            )
            second = client.post(
                "/api/v1/webhooks/logistics",
                headers={"x-api-key": "local-test-secret"},
                json=payload,
            )

        assert first.status_code == 200
        assert second.status_code == 200
        assert second.json()["result"] == "duplicate"
    finally:
        app.dependency_overrides.pop(get_db, None)
