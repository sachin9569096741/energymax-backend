from decimal import Decimal
from typing import Any

from app.modules.shop.payment.providers.base import PaymentProvider
from app.modules.shop.payment.providers.exceptions import (
    PaymentProviderError,
    PaymentProviderSignatureError,
)
from app.modules.shop.payment.providers.razorpay.client import RazorpayClient
from app.modules.shop.payment.providers.razorpay.mapper import RazorpayMapper


class RazorpayAdapter(PaymentProvider):
    """
    Razorpay implementation of the provider-agnostic
    PaymentProvider interface.
    """

    provider_name = "razorpay"

    def __init__(
        self,
        *,
        client: RazorpayClient,
        webhook_secret: str,
    ):
        self.client = client
        self.webhook_secret = webhook_secret
        self.mapper = RazorpayMapper()

    def create_payment_order(
        self,
        *,
        payment_id: str,
        amount: Decimal,
        currency: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        try:
            response = self.client.create_order(
                amount=amount,
                currency=currency,
                receipt=payment_id,
                notes=metadata,
            )

            return self.mapper.map_order_response(response)

        except PaymentProviderError:
            raise

        except Exception as exc:
            raise PaymentProviderError(
                "Failed to create Razorpay payment order.",
                provider=self.provider_name,
                code="CREATE_ORDER_FAILED",
            ) from exc

    def verify_payment(
        self,
        *,
        provider_order_id: str,
        provider_payment_id: str,
        signature: str,
    ) -> dict[str, Any]:
        try:
            self.client.verify_payment_signature(
                provider_order_id=provider_order_id,
                provider_payment_id=provider_payment_id,
                signature=signature,
            )
        except Exception as exc:
            raise PaymentProviderSignatureError(
                "Razorpay payment signature verification failed.",
                provider=self.provider_name,
                code="INVALID_PAYMENT_SIGNATURE",
            ) from exc

        try:
            response = self.client.fetch_payment(
                provider_payment_id=provider_payment_id,
            )

            return self.mapper.map_payment_response(response)

        except PaymentProviderError:
            raise

        except Exception as exc:
            raise PaymentProviderError(
                "Failed to verify Razorpay payment.",
                provider=self.provider_name,
                code="VERIFY_PAYMENT_FAILED",
            ) from exc

    def verify_webhook(
        self,
        *,
        payload: bytes,
        signature: str,
    ) -> bool:
        try:
            self.client.verify_webhook_signature(
                payload=payload,
                signature=signature,
                webhook_secret=self.webhook_secret,
            )

            return True

        except Exception as exc:
            raise PaymentProviderSignatureError(
                "Razorpay webhook signature verification failed.",
                provider=self.provider_name,
                code="INVALID_WEBHOOK_SIGNATURE",
            ) from exc

    def parse_webhook(self, *, payload: dict[str, Any]) -> dict[str, Any]:
        event_type = payload.get("event")

        if not event_type:
            raise PaymentProviderError(
                "Razorpay webhook event type is missing.",
                provider=self.provider_name,
                code="WEBHOOK_EVENT_TYPE_MISSING",
            )

        if event_type not in {
            "payment.captured",
            "payment.failed",
        }:
            raise PaymentProviderError(
                f"Unsupported Razorpay webhook event: {event_type}",
                provider=self.provider_name,
                code="UNSUPPORTED_WEBHOOK_EVENT",
            )

        payload_data = payload.get("payload")

        if not isinstance(payload_data, dict):
            raise PaymentProviderError(
                "Razorpay webhook payload data is invalid.",
                provider=self.provider_name,
                code="INVALID_WEBHOOK_PAYLOAD",
            )

        payment_data = payload_data.get("payment")

        if not isinstance(payment_data, dict):
            raise PaymentProviderError(
                "Razorpay webhook payment data is missing.",
                provider=self.provider_name,
                code="WEBHOOK_PAYMENT_DATA_MISSING",
            )

        entity = payment_data.get("entity")

        if not isinstance(entity, dict):
            raise PaymentProviderError(
                "Razorpay webhook payment entity is missing.",
                provider=self.provider_name,
                code="WEBHOOK_PAYMENT_ENTITY_MISSING",
            )

        provider_payment_id = entity.get("id")
        provider_order_id = entity.get("order_id")
        amount = entity.get("amount")
        currency = entity.get("currency")
        provider_status = entity.get("status")

        if not provider_payment_id:
            raise PaymentProviderError(
                "Razorpay webhook payment ID is missing.",
                provider=self.provider_name,
                code="WEBHOOK_PAYMENT_ID_MISSING",
            )

        if not provider_order_id:
            raise PaymentProviderError(
                "Razorpay webhook order ID is missing.",
                provider=self.provider_name,
                code="WEBHOOK_ORDER_ID_MISSING",
            )

        if amount is None:
            raise PaymentProviderError(
                "Razorpay webhook amount is missing.",
                provider=self.provider_name,
                code="WEBHOOK_AMOUNT_MISSING",
            )

        if not currency:
            raise PaymentProviderError(
                "Razorpay webhook currency is missing.",
                provider=self.provider_name,
                code="WEBHOOK_CURRENCY_MISSING",
            )

        return {
            "event_type": event_type,
            "provider_payment_id": provider_payment_id,
            "provider_order_id": provider_order_id,
            "amount": Decimal(str(amount)) / Decimal("100"),
            "currency": currency,
            "provider_status": provider_status,
            "raw_payload": payload,
        }

    def refund_payment(
        self,
        *,
        provider_payment_id: str,
        amount: Decimal | None = None,
        metadata: dict[str, Any] | None = None,
        currency: str = "INR",
    ) -> dict[str, Any]:
        try:
            response = self.client.refund_payment(
                provider_payment_id=provider_payment_id,
                amount=amount,
                notes=metadata,
            )

            return self.mapper.map_refund_response(response)

        except PaymentProviderError:
            raise

        except Exception as exc:
            raise PaymentProviderError(
                "Failed to create Razorpay refund.",
                provider=self.provider_name,
                code="REFUND_FAILED",
            ) from exc