from __future__ import annotations

from decimal import Decimal
from typing import Any


class CashfreeMapper:
    """
    Converts raw Cashfree API responses into provider-neutral structures.

    No database or business logic belongs here.
    """

    PAYMENT_STATUS_MAP: dict[str, str] = {
        "SUCCESS": "succeeded",
        "FAILED": "failed",
        "USER_DROPPED": "failed",
        "CANCELLED": "cancelled",
        "VOID": "cancelled",
        "PENDING": "pending",
        "NOT_ATTEMPTED": "pending",
        "FLAGGED": "pending",
        "ACTIVE": "pending",
    }

    REFUND_STATUS_MAP: dict[str, str] = {
        "SUCCESS": "succeeded",
        "FAILED": "failed",
        "CANCELLED": "failed",
        "PENDING": "pending",
        "INITIALIZED": "pending",
        "PROCESSING": "pending",
    }

    @staticmethod
    def _decimal(
        value: Any,
        *,
        default: Decimal | None = None,
    ) -> Decimal | None:
        if value is None:
            return default

        try:
            return Decimal(str(value))
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _string(
        value: Any,
    ) -> str | None:
        if value is None:
            return None

        value = str(value).strip()

        return value or None

    @classmethod
    def map_payment_status(
        cls,
        provider_status: Any,
    ) -> str:
        status = cls._string(provider_status)

        if not status:
            return "pending"

        normalized = status.upper()

        return cls.PAYMENT_STATUS_MAP.get(
            normalized,
            "pending",
        )

    @classmethod
    def map_refund_status(
        cls,
        provider_status: Any,
    ) -> str:
        status = cls._string(provider_status)

        if not status:
            return "pending"

        normalized = status.upper()

        return cls.REFUND_STATUS_MAP.get(
            normalized,
            "pending",
        )

    @classmethod
    def map_order_creation(
        cls,
        response: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Normalize Cashfree create-order response.

        Expected normalized structure:

        {
            "provider_order_id": str,
            "amount": Decimal | None,
            "currency": str,
            "status": str,
            "payment_session_id": str | None,
            "raw_response": dict,
        }
        """

        provider_order_id = cls._string(
            response.get("order_id")
        )

        if not provider_order_id:
            raise ValueError(
                "Cashfree order response does not contain order_id."
            )

        amount = cls._decimal(
            response.get("order_amount")
        )

        currency = (
            cls._string(
                response.get("order_currency")
            )
            or "INR"
        )

        provider_status = cls._string(
            response.get("order_status")
        )

        payment_session_id = cls._string(
            response.get("payment_session_id")
        )

        return {
            "provider_order_id": provider_order_id,
            "amount": amount,
            "currency": currency,
            "status": provider_status or "ACTIVE",
            "payment_session_id": payment_session_id,
            "raw_response": response,
        }

    @classmethod
    def map_payment(
        cls,
        response: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Normalize a Cashfree payment transaction.

        Expected normalized structure:

        {
            "provider_payment_id": str | None,
            "provider_order_id": str | None,
            "amount": Decimal | None,
            "currency": str | None,
            "status": str,
            "provider_status": str | None,
            "payment_method": dict | None,
            "raw_response": dict,
        }
        """

        provider_payment_id = cls._string(
            response.get("cf_payment_id")
        )

        provider_order_id = cls._string(
            response.get("order_id")
        )

        amount = cls._decimal(
            response.get("payment_amount")
        )

        currency = cls._string(
            response.get("payment_currency")
        )

        provider_status = cls._string(
            response.get("payment_status")
        )

        return {
            "provider_payment_id": provider_payment_id,
            "provider_order_id": provider_order_id,
            "amount": amount,
            "currency": currency,
            "status": cls.map_payment_status(
                provider_status
            ),
            "provider_status": provider_status,
            "payment_method": response.get(
                "payment_method"
            ),
            "raw_response": response,
        }

    @classmethod
    def map_refund(
        cls,
        response: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Normalize a Cashfree refund response.

        Expected normalized structure:

        {
            "provider_refund_id": str | None,
            "provider_payment_id": str | None,
            "provider_order_id": str | None,
            "amount": Decimal | None,
            "currency": str | None,
            "status": str,
            "provider_status": str | None,
            "failure_code": str | None,
            "failure_message": str | None,
            "raw_response": dict,
        }
        """

        provider_refund_id = cls._string(
            response.get("refund_id")
        )

        provider_payment_id = cls._string(
            response.get("cf_payment_id")
        )

        provider_order_id = cls._string(
            response.get("order_id")
        )

        amount = cls._decimal(
            response.get("refund_amount")
        )

        currency = cls._string(
            response.get("refund_currency")
        )

        provider_status = cls._string(
            response.get("refund_status")
        )

        failure_code = cls._string(
            response.get("refund_arn")
        )

        failure_message = cls._string(
            response.get("refund_note")
        )

        return {
            "provider_refund_id": provider_refund_id,
            "provider_payment_id": provider_payment_id,
            "provider_order_id": provider_order_id,
            "amount": amount,
            "currency": currency,
            "status": cls.map_refund_status(
                provider_status
            ),
            "provider_status": provider_status,
            "failure_code": failure_code,
            "failure_message": failure_message,
            "raw_response": response,
        }


    @classmethod
    def parse_webhook(
        cls,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Normalize a Cashfree webhook payload.

        Internal event types:

        PAYMENT_SUCCESS_WEBHOOK
            -> payment.succeeded

        PAYMENT_FAILED_WEBHOOK
            -> payment.failed

        PAYMENT_USER_DROPPED_WEBHOOK
            -> payment.failed
        """

        if not isinstance(payload, dict):
            raise ValueError(
                "Cashfree webhook payload must be an object."
            )

        event_type = cls._string(
            payload.get("type")
        )

        if not event_type:
            raise ValueError(
                "Cashfree webhook event type is missing."
            )

        data = payload.get("data")

        if not isinstance(data, dict):
            raise ValueError(
                "Cashfree webhook data is missing."
            )

        payment_data = data.get("payment")

        if not isinstance(payment_data, dict):
            raise ValueError(
                "Cashfree webhook payment data is missing."
            )

        order_data = data.get("order")

        if not isinstance(order_data, dict):
            raise ValueError(
                "Cashfree webhook order data is missing."
            )

        provider_payment_id = cls._string(
            payment_data.get("cf_payment_id")
        )

        provider_order_id = cls._string(
            order_data.get("order_id")
        )

        amount = cls._decimal(
            payment_data.get("payment_amount")
        )

        currency = cls._string(
            payment_data.get("payment_currency")
        )

        provider_status = cls._string(
            payment_data.get("payment_status")
        )

        if not provider_payment_id:
            raise ValueError(
                "Cashfree webhook payment ID is missing."
            )

        if not provider_order_id:
            raise ValueError(
                "Cashfree webhook order ID is missing."
            )

        if amount is None:
            raise ValueError(
                "Cashfree webhook payment amount is missing."
            )

        if not currency:
            raise ValueError(
                "Cashfree webhook payment currency is missing."
            )

        event_map = {
            "PAYMENT_SUCCESS_WEBHOOK": "payment.succeeded",
            "PAYMENT_FAILED_WEBHOOK": "payment.failed",
            "PAYMENT_USER_DROPPED_WEBHOOK": "payment.failed",
        }

        normalized_event_type = event_map.get(
            event_type
        )

        if normalized_event_type is None:
            raise ValueError(
                f"Unsupported Cashfree webhook event: "
                f"{event_type}"
            )

        return {
        "entity_type": "payment",
        "event_type": normalized_event_type,
        "provider_payment_id": provider_payment_id,
        "provider_order_id": provider_order_id,
        "amount": amount,
        "currency": currency,
        "status": cls.map_payment_status(
            provider_status
        ),
        "provider_status": provider_status,
        "raw_payload": payload,
    }