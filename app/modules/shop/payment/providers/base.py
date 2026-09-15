from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Any


class PaymentProvider(ABC):
    """
    Provider-agnostic contract for payment gateways.

    Every payment provider adapter must implement this interface.
    The rest of the payment module must not depend on provider-specific SDKs.
    """

    provider_name: str

    @abstractmethod
    def create_payment_order(
        self,
        *,
        payment_id: str,
        amount: Decimal,
        currency: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Create a payment/order on the provider.

        Expected normalized response:
        {
            "provider_order_id": str,
            "amount": Decimal,
            "currency": str,
            "status": str,
            "raw_response": dict,
        }
        """
        raise NotImplementedError

    @abstractmethod
    def verify_payment(
        self,
        *,
        provider_order_id: str,
        provider_payment_id: str,
        signature: str,
    ) -> dict[str, Any]:
        """
        Verify a payment with the provider.

        Expected normalized response:
        {
            "provider_payment_id": str,
            "provider_order_id": str,
            "status": str,
            "raw_response": dict,
        }
        """
        raise NotImplementedError

    @abstractmethod
    def verify_webhook(
        self,
        *,
        payload: bytes,
        signature: str,
    ) -> bool:
        """
        Verify the authenticity of a provider webhook.
        """
        raise NotImplementedError

    @abstractmethod
    def refund_payment(
        self,
        *,
        provider_payment_id: str,
        amount: Decimal | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Create a full or partial refund.

        Expected normalized response:
        {
            "provider_refund_id": str,
            "amount": Decimal,
            "status": str,
            "raw_response": dict,
        }
        """
        raise NotImplementedError

    @abstractmethod
    def parse_webhook(
        self,
        *,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Convert a provider webhook payload into a normalized structure.

        Expected normalized response:
        {
            "event_id": str,
            "event_type": str,
            "payment_id": str | None,
            "provider_order_id": str | None,
            "provider_payment_id": str | None,
            "status": str | None,
            "raw_payload": dict,
        }
        """
        raise NotImplementedError