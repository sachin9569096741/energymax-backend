from __future__ import annotations

import base64
import hashlib
import hmac
import json
from typing import Any

from app.core.config import settings
from app.modules.shop.payment.providers.base import PaymentProvider
from app.modules.shop.payment.providers.cashfree.client import CashfreeClient
from app.modules.shop.payment.providers.cashfree.mapper import CashfreeMapper
from app.modules.shop.payment.providers.exceptions import (
    PaymentProviderAuthenticationError,
    PaymentProviderError,
    PaymentProviderResponseError,
    PaymentProviderSignatureError,
)


class CashfreeAdapter(PaymentProvider):
    """
    Cashfree implementation of the provider-neutral PaymentProvider contract.

    Responsibilities:
    - Communicate with Cashfree through CashfreeClient.
    - Normalize Cashfree responses through CashfreeMapper.
    - Verify Cashfree webhook signatures.
    - Parse Cashfree payment/refund webhooks.
    - Keep database/business logic outside the provider layer.
    """

    provider_name = "cashfree"

    def __init__(
        self,
        *,
        client: CashfreeClient,
    ):
        self.client = client

    # =========================================================
    # PAYMENT ORDER
    # =========================================================

    def create_payment_order(
        self,
        *,
        payment_id: str,
        amount,
        currency: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:

        if amount is None:
            raise PaymentProviderResponseError(
                "Payment amount is required.",
                provider=self.provider_name,
                code="missing_amount",
            )

        if amount <= 0:
            raise PaymentProviderResponseError(
                "Payment amount must be greater than zero.",
                provider=self.provider_name,
                code="invalid_amount",
            )

        if not currency:
            raise PaymentProviderResponseError(
                "Payment currency is required.",
                provider=self.provider_name,
                code="missing_currency",
            )

        if currency.upper() != "INR":
            raise PaymentProviderResponseError(
                "Cashfree currently supports INR payments in this integration.",
                provider=self.provider_name,
                code="unsupported_currency",
            )

        metadata = metadata or {}

        customer_name = (
            metadata.get("customer_name")
            or "EnergyMax Customer"
        )

        customer_phone = (
            metadata.get("customer_phone")
        )

        if not customer_phone:
            raise PaymentProviderResponseError(
                "Customer phone is required for Cashfree payment creation.",
                provider=self.provider_name,
                code="missing_customer_phone",
            )

        customer_email = (
            metadata.get("customer_email")
        )

        order_id = str(
            metadata.get("order_public_id")
            or payment_id
        )

        response = self.client.create_order(
            order_id=order_id,
            order_amount=amount,
            customer_name=customer_name,
            customer_phone=str(customer_phone),
            customer_email=customer_email,
            order_note=(
                metadata.get("order_number")
            ),
            notify_url=settings.cashfree_webhook_url or None,
            idempotency_key=payment_id,
        )

        normalized = CashfreeMapper.map_order_creation(
            response
        )

        provider_order_id = normalized.get(
            "provider_order_id"
        )

        if not provider_order_id:
            raise PaymentProviderResponseError(
                "Cashfree did not return an order ID.",
                provider=self.provider_name,
                code="missing_provider_order_id",
            )

        provider_amount = normalized.get(
            "amount"
        )

        if (
            provider_amount is not None
            and provider_amount != amount
        ):
            raise PaymentProviderResponseError(
                "Cashfree returned an unexpected payment amount.",
                provider=self.provider_name,
                code="amount_mismatch",
            )

        provider_currency = normalized.get(
            "currency"
        )

        if (
            provider_currency
            and provider_currency.upper()
            != currency.upper()
        ):
            raise PaymentProviderResponseError(
                "Cashfree returned an unexpected currency.",
                provider=self.provider_name,
                code="currency_mismatch",
            )

        return normalized

    # =========================================================
    # VERIFY PAYMENT
    # =========================================================

    def verify_payment(
        self,
        *,
        provider_order_id: str,
        provider_payment_id: str | None = None,
    ) -> dict[str, Any]:

        if not provider_order_id:
            raise PaymentProviderResponseError(
                "Provider order ID is required.",
                provider=self.provider_name,
                code="missing_provider_order_id",
            )

        payments = self.client.get_payments_for_order(
            order_id=provider_order_id
        )

        if not isinstance(payments, list):
            raise PaymentProviderResponseError(
                "Cashfree returned an invalid payments response.",
                provider=self.provider_name,
                code="invalid_payments_response",
            )

        if not payments:
            return {
                "provider_payment_id": None,
                "provider_order_id": provider_order_id,
                "amount": None,
                "currency": None,
                "status": "pending",
                "provider_status": None,
                "raw_response": payments,
            }

        normalized_payments = [
            CashfreeMapper.map_payment(payment)
            for payment in payments
            if isinstance(payment, dict)
        ]

        if not normalized_payments:
            raise PaymentProviderResponseError(
                "Cashfree returned no valid payment records.",
                provider=self.provider_name,
                code="no_valid_payment_records",
            )

        selected_payment = None

        # -----------------------------------------------------
        # Prefer explicitly requested payment ID
        # -----------------------------------------------------

        if provider_payment_id:
            for payment in normalized_payments:
                if (
                    payment.get("provider_payment_id")
                    == provider_payment_id
                ):
                    selected_payment = payment
                    break

        # -----------------------------------------------------
        # Otherwise prefer successful payment
        # -----------------------------------------------------

        if selected_payment is None:
            for payment in normalized_payments:
                if payment.get("status") == "succeeded":
                    selected_payment = payment
                    break

        # -----------------------------------------------------
        # Then pending payment
        # -----------------------------------------------------

        if selected_payment is None:
            for payment in normalized_payments:
                if payment.get("status") == "pending":
                    selected_payment = payment
                    break

        # -----------------------------------------------------
        # Finally use latest returned payment
        # -----------------------------------------------------

        if selected_payment is None:
            selected_payment = normalized_payments[-1]

        selected_payment["provider_order_id"] = (
            selected_payment.get("provider_order_id")
            or provider_order_id
        )

        return selected_payment

    # =========================================================
    # REFUND PAYMENT
    # =========================================================

    def refund_payment(
        self,
        *,
        provider_order_id: str,
        provider_payment_id: str | None = None,
        amount=None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:

        if not provider_order_id:
            raise PaymentProviderResponseError(
                "Provider order ID is required for refund.",
                provider=self.provider_name,
                code="missing_provider_order_id",
            )

        if amount is None:
            raise PaymentProviderResponseError(
                "Refund amount is required.",
                provider=self.provider_name,
                code="missing_refund_amount",
            )

        if amount <= 0:
            raise PaymentProviderResponseError(
                "Refund amount must be greater than zero.",
                provider=self.provider_name,
                code="invalid_refund_amount",
            )

        metadata = metadata or {}

        refund_id = metadata.get(
            "refund_id"
        )

        if not refund_id:
            raise PaymentProviderResponseError(
                "Refund ID is required.",
                provider=self.provider_name,
                code="missing_refund_id",
            )

        refund_note = (
            metadata.get("refund_note")
            or "Customer refund"
        )

        refund_speed = (
            metadata.get("refund_speed")
            or "STANDARD"
        )

        idempotency_key = (
            metadata.get("idempotency_key")
            or refund_id
        )

        response = self.client.create_refund(
            order_id=provider_order_id,
            refund_id=str(refund_id),
            refund_amount=float(amount),
            refund_note=refund_note,
            refund_speed=refund_speed,
            idempotency_key=idempotency_key,
        )

        normalized = CashfreeMapper.map_refund(
            response
        )

        provider_refund_id = normalized.get(
            "provider_refund_id"
        )

        if not provider_refund_id:
            raise PaymentProviderResponseError(
                "Cashfree did not return a refund ID.",
                provider=self.provider_name,
                code="missing_provider_refund_id",
            )

        provider_amount = normalized.get(
            "amount"
        )

        if (
            provider_amount is not None
            and provider_amount != amount
        ):
            raise PaymentProviderResponseError(
                "Cashfree returned an unexpected refund amount.",
                provider=self.provider_name,
                code="refund_amount_mismatch",
            )

        return normalized

    # =========================================================
    # FETCH REFUND
    # =========================================================

    def fetch_refund(
        self,
        *,
        provider_order_id: str,
        provider_refund_id: str,
    ) -> dict[str, Any]:

        if not provider_order_id:
            raise PaymentProviderResponseError(
                "Provider order ID is required.",
                provider=self.provider_name,
                code="missing_provider_order_id",
            )

        if not provider_refund_id:
            raise PaymentProviderResponseError(
                "Provider refund ID is required.",
                provider=self.provider_name,
                code="missing_provider_refund_id",
            )

        response = self.client.get_refund(
            order_id=provider_order_id,
            refund_id=provider_refund_id,
        )

        normalized = CashfreeMapper.map_refund(
            response
        )

        return normalized

    # =========================================================
    # WEBHOOK SIGNATURE VERIFICATION
    # =========================================================

    def verify_webhook(
        self,
        *,
        payload: bytes,
        headers: dict[str, str],
    ) -> bool:

        signature = self._get_header(
            headers,
            "x-webhook-signature",
        )

        timestamp = self._get_header(
            headers,
            "x-webhook-timestamp",
        )

        if not signature:
            raise PaymentProviderSignatureError(
                "Cashfree webhook signature is missing.",
                provider=self.provider_name,
                code="missing_webhook_signature",
            )

        if not timestamp:
            raise PaymentProviderSignatureError(
                "Cashfree webhook timestamp is missing.",
                provider=self.provider_name,
                code="missing_webhook_timestamp",
            )

        signed_payload = (
            timestamp.encode("utf-8")
            + payload
        )

        digest = hmac.new(
            settings.cashfree_secret_key.encode(
                "utf-8"
            ),
            signed_payload,
            hashlib.sha256,
        ).digest()

        expected_signature = (
            base64.b64encode(digest)
            .decode("utf-8")
        )

        if not hmac.compare_digest(
            expected_signature,
            signature,
        ):
            raise PaymentProviderSignatureError(
                "Invalid Cashfree webhook signature.",
                provider=self.provider_name,
                code="invalid_webhook_signature",
            )

        return True

    # =========================================================
    # WEBHOOK PARSING
    # =========================================================

    def parse_webhook(
        self,
        *,
        payload: dict[str, Any],
    ) -> dict[str, Any]:

        if not isinstance(payload, dict):
            raise PaymentProviderResponseError(
                "Invalid Cashfree webhook payload.",
                provider=self.provider_name,
                code="invalid_webhook_payload",
            )

        event_type = (
            payload.get("type")
            or payload.get("event")
            or payload.get("event_type")
        )

        data = payload.get("data") or {}

        if not isinstance(data, dict):
            raise PaymentProviderResponseError(
                "Invalid Cashfree webhook data.",
                provider=self.provider_name,
                code="invalid_webhook_data",
            )

        order_data = data.get("order") or {}
        payment_data = data.get("payment") or {}
        refund_data = data.get("refund") or {}

        if not isinstance(order_data, dict):
            order_data = {}

        if not isinstance(payment_data, dict):
            payment_data = {}

        if not isinstance(refund_data, dict):
            refund_data = {}

        # =====================================================
        # REFUND WEBHOOK
        # =====================================================

        if refund_data:

            provider_refund_id = (
                refund_data.get("refund_id")
                or refund_data.get("cf_refund_id")
            )

            provider_payment_id = (
                refund_data.get("cf_payment_id")
                or payment_data.get("cf_payment_id")
            )

            provider_order_id = (
                refund_data.get("order_id")
                or order_data.get("order_id")
            )

            amount = CashfreeMapper._decimal(
                refund_data.get("refund_amount")
            )

            currency = (
                CashfreeMapper._string(
                    refund_data.get(
                        "refund_currency"
                    )
                )
                or "INR"
            )

            provider_status = (
                CashfreeMapper._string(
                    refund_data.get(
                        "refund_status"
                    )
                )
            )

            event_id = (
                CashfreeMapper._string(
                    refund_data.get(
                        "refund_id"
                    )
                )
                or self._build_webhook_event_id(
                    payload=payload,
                    entity_id=provider_order_id,
                    event_type=event_type,
                )
            )

            return {
                "event_id": event_id,
                "event_type": (
                    event_type
                    or "refund.status"
                ),
                "entity_type": "refund",
                "provider_order_id": (
                    CashfreeMapper._string(
                        provider_order_id
                    )
                ),
                "provider_payment_id": (
                    CashfreeMapper._string(
                        provider_payment_id
                    )
                ),
                "provider_refund_id": (
                    CashfreeMapper._string(
                        provider_refund_id
                    )
                ),
                "amount": amount,
                "currency": currency,
                "status": (
                    CashfreeMapper.map_refund_status(
                        provider_status
                    )
                ),
                "failure_code": (
                    CashfreeMapper._string(
                        refund_data.get(
                            "refund_arn"
                        )
                    )
                ),
                "failure_message": (
                    CashfreeMapper._string(
                        refund_data.get(
                            "refund_note"
                        )
                    )
                ),
                "raw_payload": payload,
            }

        # =====================================================
        # PAYMENT WEBHOOK
        # =====================================================

        try:
            normalized = CashfreeMapper.parse_webhook(
                payload
            )

        except ValueError as exc:
            raise PaymentProviderResponseError(
                str(exc),
                provider=self.provider_name,
                code="invalid_webhook_payload",
            ) from exc

        event_id = (
            CashfreeMapper._string(
                normalized.get(
                    "provider_payment_id"
                )
            )
            or self._build_webhook_event_id(
                payload=payload,
                entity_id=normalized.get(
                    "provider_order_id"
                ),
                event_type=normalized.get(
                    "event_type"
                ),
            )
        )

        status = normalized.get(
            "status"
        )

        failure_message = None

        if status == "failed":
            failure_message = (
                CashfreeMapper._string(
                    payment_data.get(
                        "payment_message"
                    )
                )
            )

        return {
            "event_id": event_id,
            "event_type": normalized[
                "event_type"
            ],
            "entity_type": "payment",
            "provider_order_id": normalized[
                "provider_order_id"
            ],
            "provider_payment_id": normalized[
                "provider_payment_id"
            ],
            "provider_refund_id": None,
            "amount": normalized[
                "amount"
            ],
            "currency": normalized[
                "currency"
            ],
            "status": status,
            "failure_code": failure_message,
            "failure_message": failure_message,
            "raw_payload": payload,
        }

    # =========================================================
    # INTERNAL HELPERS
    # =========================================================

    @staticmethod
    def _get_header(
        headers: dict[str, str],
        name: str,
    ) -> str | None:

        target = name.lower()

        for key, value in headers.items():
            if key.lower() == target:
                return value

        return None

    @staticmethod
    def _build_webhook_event_id(
        *,
        payload: dict[str, Any],
        entity_id: str | None,
        event_type: str | None,
    ) -> str:

        raw = json.dumps(
            {
                "entity_id": entity_id,
                "event_type": event_type,
                "payload": payload,
            },
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )

        return hashlib.sha256(
            raw.encode("utf-8")
        ).hexdigest()