
import hashlib
from datetime import datetime, timezone
from unittest.mock import MagicMock

from app.modules.affiliate.services.attribution import (
    resolve_tracking_token,
)


def test_tracking_token_resolves_by_hash(monkeypatch):
    now = datetime.now(timezone.utc)
    token = "example-random-referral-token"
    expected_hash = hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()

    click = MagicMock()
    click.affiliate_id = 12

    db = MagicMock()
    captured = {}

    def fake_scalar(statement):
        captured["statement"] = statement
        return click

    db.scalar.side_effect = fake_scalar

    monkeypatch.setattr(
        "app.modules.affiliate.services.attribution._get_active_affiliate",
        lambda session, affiliate_id: (
            object() if affiliate_id == 12 else None
        ),
    )

    result = resolve_tracking_token(db, token, now)

    assert result is click
    db.scalar.assert_called_once()

    statement = captured["statement"]
    assert statement.whereclause is not None

    # Verify the query includes the hashed token without compiling
    # the ORM statement or triggering mapper configuration.
    found_hash = False

    for element in statement.whereclause.get_children():
        right = getattr(element, "right", None)
        value = getattr(right, "value", None)

        if value == expected_hash:
            found_hash = True
            break

    assert found_hash, "Query must filter using the SHA-256 token hash"


def test_missing_token_returns_none():
    db = MagicMock()

    assert resolve_tracking_token(db, None) is None
    db.scalar.assert_not_called()


def test_unknown_or_expired_token_returns_none():
    db = MagicMock()
    db.scalar.return_value = None

    result = resolve_tracking_token(
        db,
        "unknown-or-expired-token",
        datetime.now(timezone.utc),
    )

    assert result is None
    db.scalar.assert_called_once()


def test_inactive_affiliate_token_returns_none(monkeypatch):
    click = MagicMock()
    click.affiliate_id = 12

    db = MagicMock()
    db.scalar.return_value = click

    monkeypatch.setattr(
        "app.modules.affiliate.services.attribution._get_active_affiliate",
        lambda session, affiliate_id: None,
    )

    result = resolve_tracking_token(
        db,
        "token-for-inactive-affiliate",
        datetime.now(timezone.utc),
    )

    assert result is None
