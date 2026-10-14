from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.shop.checkout.models.checkout import Checkout
from app.modules.shop.coupons.models.coupon import Coupon
from app.modules.shop.coupons.models.coupon_redemption import CouponRedemption


RESERVATION_MINUTES = 30
CENT = Decimal("0.01")


class CouponService:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def normalize_code(code: str) -> str:
        return code.strip().upper()

    def _get_checkout(
        self,
        public_id: str,
        customer_id: int,
    ) -> Checkout:
        checkout = self.db.scalar(
            select(Checkout)
            .where(
                Checkout.public_id == public_id,
                Checkout.customer_id == customer_id,
            )
            .with_for_update()
        )

        if checkout is None:
            raise HTTPException(
                status_code=404,
                detail="Checkout not found.",
            )

        if checkout.status != "created":
            raise HTTPException(
                status_code=409,
                detail=(
                    "Coupon can only be changed before "
                    "checkout is confirmed."
                ),
            )

        now = datetime.now(timezone.utc)
        expiry = checkout.expires_at

        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)

        if expiry <= now:
            checkout.status = "expired"
            raise HTTPException(
                status_code=400,
                detail="Checkout has expired.",
            )

        return checkout

    def _release_current(self, checkout: Checkout) -> None:
        redemption = self.db.scalar(
            select(CouponRedemption)
            .where(
                CouponRedemption.checkout_id == checkout.id
            )
            .with_for_update()
        )

        if redemption is not None and redemption.status == "reserved":
            redemption.status = "released"

        checkout.coupon_id = None
        checkout.coupon_code = None
        checkout.discount_amount = Decimal("0.00")

        checkout.total_amount = (
            Decimal(str(checkout.subtotal))
            + Decimal(str(checkout.shipping_amount))
            + Decimal(str(checkout.tax_amount))
        ).quantize(CENT)

    def apply(
        self,
        checkout_public_id: str,
        customer_id: int,
        code: str,
    ) -> dict:
        checkout = self._get_checkout(
            checkout_public_id,
            customer_id,
        )

        coupon_code = self.normalize_code(code)

        coupon = self.db.scalar(
            select(Coupon)
            .where(Coupon.code == coupon_code)
            .with_for_update()
        )

        if coupon is None:
            raise HTTPException(
                status_code=400,
                detail="Invalid coupon code.",
            )

        now = datetime.now(timezone.utc)

        if not coupon.is_active:
            raise HTTPException(
                status_code=400,
                detail="This coupon is inactive.",
            )

        starts = coupon.starts_at
        ends = coupon.ends_at

        if starts is not None and starts.tzinfo is None:
            starts = starts.replace(tzinfo=timezone.utc)

        if ends is not None and ends.tzinfo is None:
            ends = ends.replace(tzinfo=timezone.utc)

        if starts and starts > now:
            raise HTTPException(
                status_code=400,
                detail="This coupon is not valid yet.",
            )

        if ends and ends <= now:
            raise HTTPException(
                status_code=400,
                detail="This coupon has expired.",
            )

        subtotal = Decimal(
            str(checkout.subtotal)
        ).quantize(CENT)

        if (
            coupon.minimum_subtotal is not None
            and subtotal < Decimal(str(coupon.minimum_subtotal))
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Minimum subtotal for this coupon is "
                    f"{coupon.minimum_subtotal}."
                ),
            )

        # A reservation is live until it expires.
        # Redeemed records remain counted permanently.
        live = (
            (CouponRedemption.status == "redeemed")
            | (
                (CouponRedemption.status == "reserved")
                & (CouponRedemption.reserved_until > now)
            )
        )

        total_used = self.db.scalar(
            select(func.count(CouponRedemption.id)).where(
                CouponRedemption.coupon_id == coupon.id,
                live,
                CouponRedemption.checkout_id != checkout.id,
            )
        ) or 0

        if (
            coupon.max_redemptions is not None
            and total_used >= coupon.max_redemptions
        ):
            raise HTTPException(
                status_code=400,
                detail="This coupon has reached its usage limit.",
            )

        customer_used = self.db.scalar(
            select(func.count(CouponRedemption.id)).where(
                CouponRedemption.coupon_id == coupon.id,
                CouponRedemption.customer_id == customer_id,
                live,
                CouponRedemption.checkout_id != checkout.id,
            )
        ) or 0

        if (
            coupon.max_redemptions_per_customer is not None
            and customer_used >= coupon.max_redemptions_per_customer
        ):
            raise HTTPException(
                status_code=400,
                detail="You have reached this coupon's usage limit.",
            )

        # Replace an existing coupon reservation, if any.
        self._release_current(checkout)

        discount = (
            subtotal
            * Decimal(coupon.discount_percent)
            / Decimal("100")
        ).quantize(
            CENT,
            rounding=ROUND_HALF_UP,
        )

        discount = min(discount, subtotal)

        checkout.coupon_id = coupon.id
        checkout.coupon_code = coupon.code
        checkout.discount_amount = discount

        checkout.total_amount = (
            subtotal
            - discount
            + Decimal(str(checkout.shipping_amount))
            + Decimal(str(checkout.tax_amount))
        ).quantize(CENT)

        redemption = self.db.scalar(
            select(CouponRedemption)
            .where(
                CouponRedemption.checkout_id == checkout.id
            )
            .with_for_update()
        )

        expires_at = checkout.expires_at

        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        reserved_until = min(
            expires_at,
            now + timedelta(minutes=RESERVATION_MINUTES),
        )

        if redemption is None:
            redemption = CouponRedemption(
                coupon_id=coupon.id,
                customer_id=customer_id,
                checkout_id=checkout.id,
                status="reserved",
                discount_amount=discount,
                reserved_until=reserved_until,
            )
            self.db.add(redemption)
        else:
            redemption.coupon_id = coupon.id
            redemption.customer_id = customer_id
            redemption.status = "reserved"
            redemption.discount_amount = discount
            redemption.reserved_until = reserved_until
            redemption.order_id = None
            redemption.redeemed_at = None

        self.db.flush()

        return self._response(
            checkout,
            coupon.discount_percent,
        )

    def remove(
        self,
        checkout_public_id: str,
        customer_id: int,
    ) -> dict:
        checkout = self._get_checkout(
            checkout_public_id,
            customer_id,
        )

        self._release_current(checkout)
        self.db.flush()

        return self._response(checkout, None)

    @staticmethod
    def _response(
        checkout: Checkout,
        discount_percent: int | None,
    ) -> dict:
        return {
            "checkout_public_id": checkout.public_id,
            "coupon_code": checkout.coupon_code,
            "discount_percent": discount_percent,
            "subtotal": checkout.subtotal,
            "discount_amount": checkout.discount_amount,
            "shipping_amount": checkout.shipping_amount,
            "tax_amount": checkout.tax_amount,
            "total_amount": checkout.total_amount,
        }