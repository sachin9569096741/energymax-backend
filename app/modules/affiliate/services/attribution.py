
import hashlib
from types import SimpleNamespace
from datetime import datetime, timedelta, timezone
from typing import Callable

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.affiliate.models.affiliate import Affiliate
from app.modules.affiliate.models.affiliate_attribution import (
    AffiliateAttribution,
)
from unittest.mock import MagicMock
from app.modules.affiliate.models.affiliate_referral_click import (
    AffiliateReferralClick,
)
from app.modules.shop.coupons.models.coupon import Coupon


ATTRIBUTION_WINDOW_DAYS = 30
ATTRIBUTION_POLICY_VERSION = "last_click_coupon_fallback_v1"


class AttributionError(Exception):
    """Base exception for affiliate attribution errors."""


class AttributionNotFoundError(AttributionError):
    """No eligible affiliate attribution could be resolved."""


class AttributionAlreadyExistsError(AttributionError):
    """The order already has a final attribution record."""


# The resolver must use trusted server-side coupon-assignment data.
# It returns (affiliate_id, coupon_id) for an eligible assignment,
# or None when the coupon is not assigned to an eligible affiliate.
CouponAffiliateResolver = Callable[
    [Session, str, datetime],
    tuple[int, int] | None,
]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)



def make_click(click_id, affiliate_id, clicked_at, visitor_hash="visitor-1"):
    return SimpleNamespace(
        id=click_id,
        affiliate_id=affiliate_id,
        clicked_at=clicked_at,
        visitor_hash=visitor_hash,
    )


def make_active_affiliate(affiliate_id):
    return SimpleNamespace(
        id=affiliate_id,
        status="active",
        activated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
def _get_active_affiliate(
    db: Session,
    affiliate_id: int,
) -> Affiliate | None:
    """
    Return an affiliate only if active and activated.

    Status is checked again when the order is attributed.
    """
    return db.scalar(
        select(Affiliate).where(
            Affiliate.id == affiliate_id,
            Affiliate.status == "active",
            Affiliate.activated_at.is_not(None),
        )
    )


def _get_latest_eligible_click(
    db: Session,
    visitor_hash: str | None,
    now: datetime,
) -> AffiliateReferralClick | None:
    """
    Return the visitor's most recent click within the 30-day window.

    Affiliate eligibility is checked after selecting the latest click.
    An older click does not win if the latest click belongs to an
    affiliate who is currently inactive or not activated.
    """
    if not visitor_hash:
        return None

    cutoff = now - timedelta(days=ATTRIBUTION_WINDOW_DAYS)

    statement = (
        select(AffiliateReferralClick)
        .where(
            AffiliateReferralClick.visitor_hash == visitor_hash,
            AffiliateReferralClick.clicked_at >= cutoff,
            AffiliateReferralClick.clicked_at <= now,
        )
        .order_by(
            AffiliateReferralClick.clicked_at.desc(),
            AffiliateReferralClick.id.desc(),
        )
        .limit(1)
    )

    click = db.scalar(statement)

    if click is None:
        return None

    affiliate = _get_active_affiliate(db, click.affiliate_id)

    if affiliate is None:
        return None

    return click


def _get_valid_affiliate_coupon(
    db: Session,
    coupon_code: str | None,
    now: datetime,
    coupon_resolver: CouponAffiliateResolver | None,
) -> tuple[Affiliate, int] | None:
    """
    Resolve an affiliate coupon through a trusted assignment.

    The Coupon model alone does not establish affiliate ownership.
    Without a trusted assignment resolver, coupon fallback is disabled.
    """
    if not coupon_code or coupon_resolver is None:
        return None

    normalized_code = coupon_code.strip().upper()

    if not normalized_code:
        return None

    coupon = db.scalar(
        select(Coupon).where(
            Coupon.code == normalized_code,
            Coupon.is_active.is_(True),
        )
    )

    if coupon is None:
        return None

    if coupon.starts_at is not None:
        starts_at = coupon.starts_at

        if starts_at.tzinfo is None:
            starts_at = starts_at.replace(tzinfo=timezone.utc)

        if starts_at > now:
            return None

    if coupon.ends_at is not None:
        ends_at = coupon.ends_at

        if ends_at.tzinfo is None:
            ends_at = ends_at.replace(tzinfo=timezone.utc)

        if ends_at < now:
            return None

    assignment = coupon_resolver(db, normalized_code, now)

    if assignment is None:
        return None

    affiliate_id, assigned_coupon_id = assignment

    # The trusted assignment must reference the validated coupon.
    if assigned_coupon_id != coupon.id:
        return None

    affiliate = _get_active_affiliate(db, affiliate_id)

    if affiliate is None:
        return None

    return affiliate, coupon.id


def resolve_tracking_token(
    db: Session,
    tracking_token: str | None,
    now: datetime | None = None,
) -> AffiliateReferralClick | None:
    """
    Resolve a raw tracking token to an eligible recorded click.

    Returns None for missing, unknown, expired, future-dated, or
    inactive-affiliate tokens. The raw token is never queried directly.
    Only its SHA-256 hash is used for lookup.
    """
    if not tracking_token:
        return None

    token = tracking_token.strip()

    if not token or len(token) > 256:
        return None

    now = now or _utc_now()
    cutoff = now - timedelta(days=ATTRIBUTION_WINDOW_DAYS)

    token_hash = hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()

    click = db.scalar(
        select(AffiliateReferralClick).where(
            AffiliateReferralClick.tracking_token_hash == token_hash,
            AffiliateReferralClick.clicked_at >= cutoff,
            AffiliateReferralClick.clicked_at <= now,
        )
    )

    if click is None:
        return None

    # Re-check affiliate eligibility at resolution time.
    if _get_active_affiliate(db, click.affiliate_id) is None:
        return None

    return click


def attribute_order(
    db: Session,
    *,
    order_id: int,
    visitor_hash: str | None,
    tracking_token: str | None = None,
    coupon_code: str | None = None,
    coupon_resolver: CouponAffiliateResolver | None = None,
    now: datetime | None = None,
) -> AffiliateAttribution | None:
    """
    Resolve and persist one affiliate attribution for an order.

    Priority:
      1. Valid tracking token identifying an eligible click.
      2. Latest eligible active-affiliate click matching visitor_hash.
      3. Valid affiliate coupon, but only if no click wins.

    A valid token takes priority over visitor-hash matching. If the token
    is missing or invalid, the existing visitor-hash behavior is retained.

    If a valid click wins but the coupon belongs to another affiliate,
    click attribution is preserved and coupon_conflict is recorded.

    Returns None when no eligible attribution exists.

    The caller owns the transaction. This function flushes but does
    not commit.
    """
    now = now or _utc_now()

    existing = db.scalar(
        select(AffiliateAttribution).where(
            AffiliateAttribution.order_id == order_id
        )
    )

    if existing is not None:
        raise AttributionAlreadyExistsError(
            f"Order {order_id} already has affiliate attribution."
        )

    # Prefer the exact click identified by the opaque tracking token.
    click = resolve_tracking_token(
        db=db,
        tracking_token=tracking_token,
        now=now,
    )

    # Preserve the existing visitor-hash fallback.
    if click is None:
        click = _get_latest_eligible_click(
            db=db,
            visitor_hash=visitor_hash,
            now=now,
        )

    selected_affiliate: Affiliate | None = None
    selected_click_id: int | None = None
    selected_coupon_id: int | None = None
    source: str | None = None
    coupon_conflict = False

    # A valid click takes priority over coupon attribution.
    if click is not None:
        selected_affiliate = _get_active_affiliate(
            db,
            click.affiliate_id,
        )

        if selected_affiliate is not None:
            selected_click_id = click.id
            source = "CLICK"

    # Coupon fallback is used only when no eligible click was selected.
    if selected_affiliate is None:
        coupon_result = _get_valid_affiliate_coupon(
            db=db,
            coupon_code=coupon_code,
            now=now,
            coupon_resolver=coupon_resolver,
        )

        if coupon_result is None:
            return None

        selected_affiliate, selected_coupon_id = coupon_result
        source = "COUPON"

    # Keep click attribution if a different affiliate's valid coupon
    # was used, and record the conflict.
    if source == "CLICK" and coupon_code and coupon_resolver:
        coupon_result = _get_valid_affiliate_coupon(
            db=db,
            coupon_code=coupon_code,
            now=now,
            coupon_resolver=coupon_resolver,
        )

        if coupon_result is not None:
            coupon_affiliate, coupon_id = coupon_result
            selected_coupon_id = coupon_id
            coupon_conflict = (
                coupon_affiliate.id != selected_affiliate.id
            )

    attribution = AffiliateAttribution(
        order_id=order_id,
        affiliate_id=selected_affiliate.id,
        click_id=selected_click_id,
        coupon_id=selected_coupon_id,
        source=source,
        coupon_conflict=coupon_conflict,
        attributed_at=now,
        policy_version=ATTRIBUTION_POLICY_VERSION,
    )

    db.add(attribution)

    try:
        db.flush()
    except IntegrityError as exc:
        # The caller remains responsible for transaction rollback.
        # This preserves the existing exception behavior.
        raise AttributionAlreadyExistsError(
            f"Could not create attribution for order {order_id}; "
            "check whether attribution already exists or a referenced "
            "record is invalid."
        ) from exc

    return attribution



def test_valid_tracking_token_wins_over_visitor_hash(monkeypatch, now):
    token_click = make_click(
        101, 10, now - timedelta(minutes=5)
    )
    visitor_click = make_click(
        202, 20, now - timedelta(minutes=10)
    )

    db = MagicMock()
    db.scalar.return_value = None

    monkeypatch.setattr(
        "app.modules.affiliate.services.attribution.resolve_tracking_token",
        lambda db, tracking_token, now: token_click,
    )

    monkeypatch.setattr(
        "app.modules.affiliate.services.attribution._get_latest_eligible_click",
        lambda db, visitor_hash, now: visitor_click,
    )

    monkeypatch.setattr(
        "app.modules.affiliate.services.attribution._get_active_affiliate",
        lambda db, affiliate_id: make_active_affiliate(affiliate_id),
    )

    result = attribute_order(
        db,
        order_id=901,
        visitor_hash="visitor-1",
        tracking_token="valid-token",
        now=now,
    )

    assert result is not None
    assert result.affiliate_id == 10
    assert result.click_id == 101
    assert result.source == "CLICK"
    db.add.assert_called_once()
    db.flush.assert_called_once()


def test_invalid_tracking_token_falls_back_to_visitor_hash(
    monkeypatch, now
):
    visitor_click = make_click(
        202, 20, now - timedelta(minutes=10)
    )

    db = MagicMock()
    db.scalar.return_value = None

    monkeypatch.setattr(
        "app.modules.affiliate.services.attribution.resolve_tracking_token",
        lambda db, tracking_token, now: None,
    )

    monkeypatch.setattr(
        "app.modules.affiliate.services.attribution._get_latest_eligible_click",
        lambda db, visitor_hash, now: visitor_click,
    )

    monkeypatch.setattr(
        "app.modules.affiliate.services.attribution._get_active_affiliate",
        lambda db, affiliate_id: make_active_affiliate(affiliate_id),
    )

    result = attribute_order(
        db,
        order_id=902,
        visitor_hash="visitor-1",
        tracking_token="invalid-token",
        now=now,
    )

    assert result is not None
    assert result.affiliate_id == 20
    assert result.click_id == 202
    assert result.source == "CLICK"
    db.add.assert_called_once()
    db.flush.assert_called_once()
