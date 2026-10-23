
from datetime import datetime, timedelta, timezone

import pytest

from app.modules.affiliate.services import attribution as service


class FakeColumn:
    """Minimal stand-in for a SQLAlchemy ORM column."""

    def __init__(self, name: str):
        self.name = name

    def __eq__(self, other):
        return ("eq", self.name, other)


class FakeStatement:
    """Minimal stand-in for a SQLAlchemy Select statement."""

    def __init__(self, model=None):
        self.model = model
        self.conditions = []

    def where(self, *conditions):
        self.conditions.extend(conditions)
        return self

    def order_by(self, *expressions):
        return self

    def limit(self, value):
        return self


class FakeAttribution:
    """Lightweight attribution model for isolated unit tests."""

    order_id = FakeColumn("order_id")

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def _make_affiliate(
    affiliate_id=10,
    *,
    is_active=True,
    is_activated=True,
):
    """Create a lightweight affiliate object for tests."""

    return type(
        "FakeAffiliate",
        (),
        {
            "id": affiliate_id,
            "is_active": is_active,
            "is_activated": is_activated,
            "status": "active" if is_active else "inactive",
            "activated_at": (
                datetime(2026, 1, 1, tzinfo=timezone.utc)
                if is_activated
                else None
            ),
        },
    )()


def _make_click(
    *,
    affiliate_id=10,
    clicked_at=None,
    tracking_token_hash=None,
    click_id=100,
):
    """Create a lightweight referral click."""

    return type(
        "FakeClick",
        (),
        {
            "id": click_id,
            "affiliate_id": affiliate_id,
            "clicked_at": clicked_at or datetime.now(timezone.utc),
            "tracking_token_hash": tracking_token_hash,
            "visitor_hash": "visitor-hash",
        },
    )()


def _install_common_mocks(
    monkeypatch,
    *,
    existing_attribution=None,
):
    """Install SQLAlchemy and affiliate mocks for isolated unit tests."""

    monkeypatch.setattr(
        service,
        "select",
        lambda *args, **kwargs: FakeStatement(
            args[0] if args else None
        ),
    )

    monkeypatch.setattr(
        service,
        "AffiliateAttribution",
        FakeAttribution,
    )

    class FakeResult:
        def __init__(self, value=None):
            self.value = value

        def scalar_one_or_none(self):
            return self.value

        def scalars(self):
            return self

        def all(self):
            if self.value is None:
                return []

            if isinstance(self.value, list):
                return self.value

            return [self.value]

        def first(self):
            if isinstance(self.value, list):
                return self.value[0] if self.value else None

            return self.value

    class FakeDB:
        def __init__(self):
            self.added = []
            self.flush_count = 0
            self.existing_attribution = existing_attribution

        def scalar(self, statement):
            """
            Simulate SQLAlchemy Session.scalar().

            The existing attribution is returned for the duplicate-order
            check. Other scalar queries return None unless a test overrides
            the relevant service function.
            """
            if self.existing_attribution is not None:
                return self.existing_attribution

            return None

        def execute(self, statement):
            return FakeResult(self.existing_attribution)

        def add(self, obj):
            self.added.append(obj)

        def flush(self):
            self.flush_count += 1

    # The attribution service revalidates the selected affiliate before
    # persisting attribution. Return an active affiliate by default.
    monkeypatch.setattr(
        service,
        "_get_active_affiliate",
        lambda db, affiliate_id: _make_affiliate(
            affiliate_id=affiliate_id,
            is_active=True,
            is_activated=True,
        ),
    )

    return FakeDB()


def test_latest_eligible_click_is_selected(monkeypatch):
    """The mocked latest-click lookup returns the selected click."""

    now = datetime.now(timezone.utc)

    latest_click = _make_click(
        affiliate_id=20,
        clicked_at=now - timedelta(hours=1),
        click_id=200,
    )

    older_click = _make_click(
        affiliate_id=10,
        clicked_at=now - timedelta(days=2),
        click_id=100,
    )

    monkeypatch.setattr(
        service,
        "_get_latest_eligible_click",
        lambda **kwargs: latest_click,
    )

    result = service._get_latest_eligible_click(
        db=None,
        visitor_hash="visitor-hash",
        now=now,
    )

    assert result is latest_click
    assert older_click is not latest_click


def test_no_visitor_hash_returns_no_click(monkeypatch):
    """A missing visitor hash should not produce a click attribution."""

    monkeypatch.setattr(
        service,
        "_get_latest_eligible_click",
        lambda **kwargs: None,
    )

    result = service._get_latest_eligible_click(
        db=None,
        visitor_hash=None,
        now=datetime.now(timezone.utc),
    )

    assert result is None


def test_inactive_affiliate_click_is_not_eligible(monkeypatch):
    """An inactive affiliate must not receive attribution."""

    inactive_affiliate = _make_affiliate(
        affiliate_id=10,
        is_active=False,
        is_activated=True,
    )

    click = _make_click(affiliate_id=10)

    monkeypatch.setattr(
        service,
        "_get_latest_eligible_click",
        lambda **kwargs: None,
    )

    result = service._get_latest_eligible_click(
        db=None,
        visitor_hash="visitor-hash",
        now=datetime.now(timezone.utc),
    )

    assert result is None
    assert inactive_affiliate.is_active is False
    assert click.affiliate_id == inactive_affiliate.id


def test_order_with_existing_attribution_is_rejected(monkeypatch):
    """An order must not receive duplicate affiliate attribution."""

    existing = FakeAttribution(
        order_id=123,
        affiliate_id=10,
    )

    db = _install_common_mocks(
        monkeypatch,
        existing_attribution=existing,
    )

    with pytest.raises(service.AttributionAlreadyExistsError):
        service.attribute_order(
            db,
            order_id=123,
            visitor_hash="visitor-hash",
        )

    assert db.added == []
    assert db.flush_count == 0


def test_order_without_click_or_assigned_coupon_returns_none(monkeypatch):
    """No eligible click or coupon should result in no attribution."""

    db = _install_common_mocks(monkeypatch)

    monkeypatch.setattr(
        service,
        "resolve_tracking_token",
        lambda **kwargs: None,
    )

    monkeypatch.setattr(
        service,
        "_get_latest_eligible_click",
        lambda **kwargs: None,
    )

    result = service.attribute_order(
        db,
        order_id=123,
        visitor_hash="visitor-hash",
        tracking_token=None,
        coupon_code=None,
    )

    assert result is None
    assert db.added == []
    assert db.flush_count == 0


def test_no_attribution_does_not_flush(monkeypatch):
    """The database must not be flushed when attribution is unavailable."""

    db = _install_common_mocks(monkeypatch)

    monkeypatch.setattr(
        service,
        "resolve_tracking_token",
        lambda **kwargs: None,
    )

    monkeypatch.setattr(
        service,
        "_get_latest_eligible_click",
        lambda **kwargs: None,
    )

    result = service.attribute_order(
        db,
        order_id=124,
        visitor_hash=None,
        tracking_token=None,
        coupon_code=None,
    )

    assert result is None
    assert db.added == []
    assert db.flush_count == 0


def test_valid_tracking_token_wins_over_visitor_hash(monkeypatch):
    """A valid tracking token takes priority over visitor lookup."""

    token_click = _make_click(
        affiliate_id=20,
        click_id=200,
    )

    visitor_click = _make_click(
        affiliate_id=10,
        click_id=100,
    )

    db = _install_common_mocks(monkeypatch)

    monkeypatch.setattr(
        service,
        "resolve_tracking_token",
        lambda **kwargs: token_click,
    )

    monkeypatch.setattr(
        service,
        "_get_latest_eligible_click",
        lambda **kwargs: visitor_click,
    )

    result = service.attribute_order(
        db,
        order_id=125,
        visitor_hash="visitor-hash",
        tracking_token="valid-tracking-token",
    )

    assert result is not None
    assert result.affiliate_id == token_click.affiliate_id
    assert result.click_id == token_click.id
    assert result.source == "CLICK"
    assert result.coupon_conflict is False
    assert len(db.added) == 1
    assert db.flush_count == 1


def test_invalid_tracking_token_falls_back_to_visitor_hash(monkeypatch):
    """An invalid token should fall back to visitor-hash attribution."""

    visitor_click = _make_click(
        affiliate_id=10,
        click_id=100,
    )

    db = _install_common_mocks(monkeypatch)

    monkeypatch.setattr(
        service,
        "resolve_tracking_token",
        lambda **kwargs: None,
    )

    monkeypatch.setattr(
        service,
        "_get_latest_eligible_click",
        lambda **kwargs: visitor_click,
    )

    result = service.attribute_order(
        db,
        order_id=126,
        visitor_hash="visitor-hash",
        tracking_token="invalid-tracking-token",
    )

    assert result is not None
    assert result.affiliate_id == visitor_click.affiliate_id
    assert result.click_id == visitor_click.id
    assert result.source == "CLICK"
    assert result.coupon_conflict is False
    assert len(db.added) == 1
    assert db.flush_count == 1


def test_click_wins_and_records_coupon_conflict(monkeypatch):
    """Click attribution wins when a valid coupon belongs to another affiliate."""

    click = _make_click(
        affiliate_id=10,
        click_id=100,
    )

    db = _install_common_mocks(monkeypatch)

    monkeypatch.setattr(
        service,
        "resolve_tracking_token",
        lambda **kwargs: None,
    )

    monkeypatch.setattr(
        service,
        "_get_latest_eligible_click",
        lambda **kwargs: click,
    )

    # Isolate conflict handling from the actual coupon database lookup.
    # The resolver represents a trusted assignment to affiliate 20.
    monkeypatch.setattr(
        service,
        "_get_valid_affiliate_coupon",
        lambda db, coupon_code, now, coupon_resolver: (
            _make_affiliate(
                affiliate_id=20,
                is_active=True,
                is_activated=True,
            ),
            501,
        ),
    )

    result = service.attribute_order(
        db,
        order_id=127,
        visitor_hash="visitor-hash",
        coupon_code="SAVE10",
        coupon_resolver=lambda *args, **kwargs: (20, 501),
    )

    assert result is not None
    assert result.affiliate_id == 10
    assert result.click_id == click.id
    assert result.coupon_id == 501
    assert result.source == "CLICK"
    assert result.coupon_conflict is True
    assert len(db.added) == 1
    assert db.flush_count == 1
