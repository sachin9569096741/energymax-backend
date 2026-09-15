from decimal import Decimal
from typing import Any

from app.modules.shop.payment.providers.exceptions import (
    PaymentProviderResponseError,
)


class RazorpayMapper:
    """
    Converts Razorpay API responses into the normalized
    structure expected by our payment system.
    """

    @staticmethod
    def map_order_response(
        response: dict[str, Any],
    ) -> dict[str, Any]:
        provider_order_id = response.get("id")

        if not provider_order_id:
            raise PaymentProviderResponseError(
                "Razorpay order response does not contain an order ID.",
                provider="razorpay",
                code="MISSING_ORDER_ID",
            )

        amount = response.get("amount")

        if amount is None:
            raise PaymentProviderResponseError(
                "Razorpay order response does not contain an amount.",
                provider="razorpay",
                code="MISSING_AMOUNT",
            )

        currency = response.get("currency")

        if not currency:
            raise PaymentProviderResponseError(
                "Razorpay order response does not contain a currency.",
                provider="razorpay",
                code="MISSING_CURRENCY",
            )

        return {
            "provider_order_id": provider_order_id,
            "amount": Decimal(str(amount)) / Decimal("100"),
            "currency": currency,
            "status": response.get("status", "created"),
            "raw_response": response,
        }

    @staticmethod
    def map_payment_response(
        response: dict[str, Any],
    ) -> dict[str, Any]:
        provider_payment_id = response.get("id")

        if not provider_payment_id:
            raise PaymentProviderResponseError(
                "Razorpay payment response does not contain a payment ID.",
                provider="razorpay",
                code="MISSING_PAYMENT_ID",
            )

        provider_order_id = response.get("order_id")

        if not provider_order_id:
            raise PaymentProviderResponseError(
                "Razorpay payment response does not contain an order ID.",
                provider="razorpay",
                code="MISSING_ORDER_ID",
            )

        amount = response.get("amount")

        if amount is None:
            raise PaymentProviderResponseError(
                "Razorpay payment response does not contain an amount.",
                provider="razorpay",
                code="MISSING_AMOUNT",
            )

        currency = response.get("currency")

        if not currency:
            raise PaymentProviderResponseError(
                "Razorpay payment response does not contain a currency.",
                provider="razorpay",
                code="MISSING_CURRENCY",
            )

        status = response.get("status")

        if not status:
            raise PaymentProviderResponseError(
                "Razorpay payment response does not contain a status.",
                provider="razorpay",
                code="MISSING_STATUS",
            )

        return {
            "provider_payment_id": provider_payment_id,
            "provider_order_id": provider_order_id,
            "amount": Decimal(str(amount)) / Decimal("100"),
            "currency": currency,
            "status": status,
            "raw_response": response,
        }

    @staticmethod
    def map_refund_response(
        response: dict[str, Any],
    ) -> dict[str, Any]:
        provider_refund_id = response.get("id")

        if not provider_refund_id:
            raise PaymentProviderResponseError(
                "Razorpay refund response does not contain a refund ID.",
                provider="razorpay",
                code="MISSING_REFUND_ID",
            )

        amount = response.get("amount")

        if amount is None:
            raise PaymentProviderResponseError(
                "Razorpay refund response does not contain an amount.",
                provider="razorpay",
                code="MISSING_AMOUNT",
            )

        currency = response.get("currency")

        if not currency:
            raise PaymentProviderResponseError(
                "Razorpay refund response does not contain a currency.",
                provider="razorpay",
                code="MISSING_CURRENCY",
            )

        return {
            "provider_refund_id": provider_refund_id,
            "amount": Decimal(str(amount)) / Decimal("100"),
            "currency": currency,
            "status": response.get("status"),
            "raw_response": response,
        }