from decimal import Decimal
from typing import Any

import razorpay


class RazorpayClient:
    """
    Low-level Razorpay API client.

    This class is responsible only for communicating with Razorpay.
    Business logic belongs in the adapter/service layer.
    """

    def __init__(
        self,
        *,
        key_id: str,
        key_secret: str,
    ):
        self.key_id = key_id
        self.key_secret = key_secret

        self.client = razorpay.Client(
            auth=(key_id, key_secret),
        )

    def create_order(
        self,
        *,
        amount: Decimal,
        currency: str,
        receipt: str,
        notes: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """
        Create an order on Razorpay.

        Razorpay expects amount in the smallest currency unit.
        For INR, that means paise.
        """

        amount_in_paise = int(
            amount * Decimal("100")
        )

        payload: dict[str, Any] = {
            "amount": amount_in_paise,
            "currency": currency,
            "receipt": receipt,
        }

        if notes:
            payload["notes"] = notes

        return self.client.order.create(payload)

    def fetch_payment(
        self,
        *,
        provider_payment_id: str,
    ) -> dict[str, Any]:
        """
        Fetch a payment from Razorpay.
        """

        return self.client.payment.fetch(
            provider_payment_id
        )

    def refund_payment(
        self,
        *,
        provider_payment_id: str,
        amount: Decimal | None = None,
        notes: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """
        Create a full or partial refund on Razorpay.
        """

        if amount is None:
            return self.client.payment.refund(
                provider_payment_id
            )

        amount_in_paise = int(
            amount * Decimal("100")
        )

        payload: dict[str, Any] = {
            "amount": amount_in_paise,
        }

        if notes:
            payload["notes"] = notes

        return self.client.payment.refund(
            provider_payment_id,
            payload,
        )

    def verify_payment_signature(
        self,
        *,
        provider_order_id: str,
        provider_payment_id: str,
        signature: str,
    ) -> None:
        """
        Verify Razorpay payment signature.

        Razorpay raises an exception if the signature is invalid.
        """

        self.client.utility.verify_payment_signature(
            {
                "razorpay_order_id": provider_order_id,
                "razorpay_payment_id": provider_payment_id,
                "razorpay_signature": signature,
            }
        )

    def verify_webhook_signature(
        self,
        *,
        payload: bytes,
        signature: str,
        webhook_secret: str,
    ) -> None:
        """
        Verify Razorpay webhook signature.
        """

        self.client.utility.verify_webhook_signature(
            payload.decode("utf-8"),
            signature,
            webhook_secret,
        )