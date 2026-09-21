from __future__ import annotations

from decimal import Decimal
from typing import Any

import httpx

from app.core.config import settings
from app.modules.shop.payment.providers.exceptions import (
    PaymentProviderAuthenticationError,
    PaymentProviderConnectionError,
    PaymentProviderResponseError,
    PaymentProviderTimeoutError,
    PaymentProviderValidationError,
)


class CashfreeClient:
    """
    Low-level Cashfree Payments API client.

    This class is responsible only for HTTP communication with Cashfree.
    Business logic and payment state transitions belong in the adapter/service.
    """

    def __init__(
        self,
        *,
        app_id: str,
        secret_key: str,
        environment: str = "sandbox",
        api_version: str = "2025-01-01",
        timeout: float = 15.0,
    ):
        self.app_id = app_id
        self.secret_key = secret_key
        self.environment = environment.lower().strip()
        self.api_version = api_version
        self.timeout = timeout

        if self.environment == "production":
            self.base_url = "https://api.cashfree.com/pg"
        else:
            self.base_url = "https://sandbox.cashfree.com/pg"

    def _headers(
        self,
        *,
        idempotency_key: str | None = None,
    ) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "x-client-id": self.app_id,
            "x-client-secret": self.secret_key,
            "x-api-version": self.api_version,
        }

        if idempotency_key:
            headers["x-idempotency-key"] = idempotency_key

        return headers

    def _handle_response(
        self,
        response: httpx.Response,
    ) -> dict[str, Any] | list[Any]:
        if response.status_code in {401, 403}:
            raise PaymentProviderAuthenticationError(
                "Cashfree authentication failed.",
                provider="cashfree",
                code=str(response.status_code),
            )

        if response.status_code == 400:
            raise PaymentProviderValidationError(
                self._extract_error_message(response),
                provider="cashfree",
                code=str(response.status_code),
            )

        if response.status_code == 404:
            raise PaymentProviderResponseError(
                self._extract_error_message(response),
                provider="cashfree",
                code="404",
            )

        if response.status_code >= 500:
            raise PaymentProviderResponseError(
                "Cashfree returned a server error.",
                provider="cashfree",
                code=str(response.status_code),
            )

        if response.status_code >= 400:
            raise PaymentProviderResponseError(
                self._extract_error_message(response),
                provider="cashfree",
                code=str(response.status_code),
            )

        try:
            return response.json()
        except ValueError as exc:
            raise PaymentProviderResponseError(
                "Cashfree returned an invalid JSON response.",
                provider="cashfree",
                code="invalid_json",
            ) from exc

    @staticmethod
    def _extract_error_message(response: httpx.Response) -> str:
        try:
            data = response.json()
        except ValueError:
            return response.text or "Cashfree API request failed."

        if isinstance(data, dict):
            for key in (
                "message",
                "error_description",
                "error",
                "type",
            ):
                value = data.get(key)
                if value:
                    return str(value)

        return response.text or "Cashfree API request failed."

    def create_order(
        self,
        *,
        order_id: str,
        order_amount: Decimal,
        customer_name: str,
        customer_phone: str,
        customer_email: str | None = None,
        return_url: str | None = None,
        notify_url: str | None = None,
        order_note: str | None = None,
        order_tags: dict[str, str] | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "order_id": order_id,
            "order_amount": float(order_amount),
            "order_currency": "INR",
            "customer_details": {
                "customer_id": order_id,
                "customer_name": customer_name,
                "customer_phone": customer_phone,
            },
        }

        if customer_email:
            payload["customer_details"]["customer_email"] = customer_email

        if return_url:
            payload["order_meta"] = {
                "return_url": return_url,
            }

        if notify_url:
            payload.setdefault("order_meta", {})
            payload["order_meta"]["notify_url"] = notify_url

        if order_note:
            payload["order_note"] = order_note

        if order_tags:
            payload["order_tags"] = order_tags

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.base_url}/orders",
                    headers=self._headers(
                        idempotency_key=idempotency_key,
                    ),
                    json=payload,
                )

        except httpx.TimeoutException as exc:
            raise PaymentProviderTimeoutError(
                "Cashfree order creation timed out.",
                provider="cashfree",
                code="timeout",
            ) from exc

        except httpx.RequestError as exc:
            raise PaymentProviderConnectionError(
                "Could not connect to Cashfree.",
                provider="cashfree",
                code="connection_error",
            ) from exc

        result = self._handle_response(response)

        if not isinstance(result, dict):
            raise PaymentProviderResponseError(
                "Cashfree order response must be an object.",
                provider="cashfree",
                code="invalid_response",
            )

        return result

    def get_payments_for_order(
        self,
        *,
        order_id: str,
    ) -> list[dict[str, Any]]:
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(
                    f"{self.base_url}/orders/{order_id}/payments",
                    headers=self._headers(),
                )

        except httpx.TimeoutException as exc:
            raise PaymentProviderTimeoutError(
                "Cashfree payment status request timed out.",
                provider="cashfree",
                code="timeout",
            ) from exc

        except httpx.RequestError as exc:
            raise PaymentProviderConnectionError(
                "Could not connect to Cashfree.",
                provider="cashfree",
                code="connection_error",
            ) from exc

        result = self._handle_response(response)

        if not isinstance(result, list):
            raise PaymentProviderResponseError(
                "Cashfree payments response must be a list.",
                provider="cashfree",
                code="invalid_response",
            )

        return result

    def get_order(
        self,
        *,
        order_id: str,
    ) -> dict[str, Any]:
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(
                    f"{self.base_url}/orders/{order_id}",
                    headers=self._headers(),
                )

        except httpx.TimeoutException as exc:
            raise PaymentProviderTimeoutError(
                "Cashfree order status request timed out.",
                provider="cashfree",
                code="timeout",
            ) from exc

        except httpx.RequestError as exc:
            raise PaymentProviderConnectionError(
                "Could not connect to Cashfree.",
                provider="cashfree",
                code="connection_error",
            ) from exc

        result = self._handle_response(response)

        if not isinstance(result, dict):
            raise PaymentProviderResponseError(
                "Cashfree order response must be an object.",
                provider="cashfree",
                code="invalid_response",
            )

        return result

    def create_refund(
        self,
        *,
        order_id: str,
        refund_id: str,
        refund_amount: Decimal,
        refund_note: str | None = None,
        refund_speed: str = "STANDARD",
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "refund_id": refund_id,
            "refund_amount": float(refund_amount),
            "refund_speed": refund_speed,
        }

        if refund_note:
            payload["refund_note"] = refund_note

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.base_url}/orders/{order_id}/refunds",
                    headers=self._headers(
                        idempotency_key=idempotency_key,
                    ),
                    json=payload,
                )

        except httpx.TimeoutException as exc:
            raise PaymentProviderTimeoutError(
                "Cashfree refund request timed out.",
                provider="cashfree",
                code="timeout",
            ) from exc

        except httpx.RequestError as exc:
            raise PaymentProviderConnectionError(
                "Could not connect to Cashfree.",
                provider="cashfree",
                code="connection_error",
            ) from exc

        result = self._handle_response(response)

        if not isinstance(result, dict):
            raise PaymentProviderResponseError(
                "Cashfree refund response must be an object.",
                provider="cashfree",
                code="invalid_response",
            )

        return result

    def get_refund(
        self,
        *,
        order_id: str,
        refund_id: str,
    ) -> dict[str, Any]:
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(
                    f"{self.base_url}/orders/{order_id}/refunds/{refund_id}",
                    headers=self._headers(),
                )

        except httpx.TimeoutException as exc:
            raise PaymentProviderTimeoutError(
                "Cashfree refund lookup timed out.",
                provider="cashfree",
                code="timeout",
            ) from exc

        except httpx.RequestError as exc:
            raise PaymentProviderConnectionError(
                "Could not connect to Cashfree.",
                provider="cashfree",
                code="connection_error",
            ) from exc

        result = self._handle_response(response)

        if not isinstance(result, dict):
            raise PaymentProviderResponseError(
                "Cashfree refund response must be an object.",
                provider="cashfree",
                code="invalid_response",
            )

        return result