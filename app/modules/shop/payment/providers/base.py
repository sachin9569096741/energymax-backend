from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Any


class PaymentProvider(ABC):
    """
    Provider-agnostic contract for payment gateways.

    Every payment provider adapter must implement this interface.
    The rest of the payment module must not depend on
    provider-specific SDKs.
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
        Create a provider-side payment order.

        Expected normalized response:
        {
            "provider_order_id": str,
            "amount": Decimal,
            "currency": str,
            "status": str,
            "payment_session_id": str | None,
            "raw_response": dict,
        }
        """
        raise NotImplementedError

    @abstractmethod
    def verify_payment(
        self,
        *,
        provider_order_id: str,
        provider_payment_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Retrieve/verify payment status from the provider.

        Expected normalized response:
        {
            "provider_payment_id": str | None,
            "provider_order_id": str,
            "amount": Decimal | None,
            "currency": str | None,
            "status": str,
            "provider_status": str | None,
            "raw_response": dict,
        }
        """
        raise NotImplementedError

    @abstractmethod
    def refund_payment(
        self,
        *,
        provider_order_id: str,
        provider_payment_id: str | None = None,
        amount: Decimal | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Create a full or partial refund.

        Expected normalized response:
        {
            "provider_refund_id": str,
            "provider_payment_id": str | None,
            "provider_order_id": str | None,
            "amount": Decimal,
            "currency": str,
            "status": str,
            "failure_code": str | None,
            "failure_message": str | None,
            "raw_response": dict,
        }
        """
        raise NotImplementedError

    @abstractmethod
    def fetch_refund(
        self,
        *,
        provider_order_id: str,
        provider_refund_id: str,
    ) -> dict[str, Any]:
        """
        Retrieve an existing refund from the provider.
        """
        raise NotImplementedError

    @abstractmethod
    def verify_webhook(
        self,
        *,
        payload: bytes,
        headers: dict[str, str],
    ) -> bool:
        """
        Verify the authenticity of a provider webhook.
        """
        raise NotImplementedError

    @abstractmethod
    def parse_webhook(
        self,
        *,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Convert provider webhook data into a normalized structure.

        Expected normalized response:
        {
            "event_id": str,
            "event_type": str,
            "entity_type": str,
            "provider_order_id": str | None,
            "provider_payment_id": str | None,
            "provider_refund_id": str | None,
            "amount": Decimal | None,
            "currency": str | None,
            "status": str | None,
            "failure_code": str | None,
            "failure_message": str | None,
            "raw_payload": dict,
        }
        """
        raise NotImplementedError