from __future__ import annotations

import base64
import hashlib
import hmac
from decimal import Decimal
from typing import Any

from app.core.config import settings
from app.modules.shop.payment.providers.base import PaymentProvider
from app.modules.shop.payment.providers.cashfree.client import CashfreeClient
from app.modules.shop.payment.providers.cashfree.mapper import CashfreeMapper
from app.modules.shop.payment.providers.exceptions import (
    PaymentProviderResponseError,
    PaymentProviderSignatureError,
)


class CashfreeAdapter(PaymentProvider):
    """
    Cashfree implementation of the provider-agnostic payment contract.
    """

    provider_name = "cashfree"

    def __init__(
        self,
        *,
        client: CashfreeClient,

    ):
        self.client = client


    # =========================================================
    # CREATE PAYMENT ORDER
    # =========================================================

    def create_payment_order(
        self,
        *,
        payment_id: str,
        amount: Decimal,
        currency: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:

        metadata = metadata or {}

        order_id = metadata.get("provider_order_id") or payment_id

        customer_name = (
            metadata.get("customer_name")
            or "EnergyMax Customer"
        )

        customer_phone = metadata.get("customer_phone")

        if not customer_phone:
            raise PaymentProviderResponseError(
                "Customer phone is required for Cashfree order creation.",
                provider="cashfree",
                code="missing_customer_phone",
            )

        customer_email = metadata.get("customer_email")

        return_url = metadata.get("return_url")
        notify_url = metadata.get("notify_url")

        order_note = metadata.get("order_note")

        order_tags = metadata.get("order_tags")

        if order_tags is not None and not isinstance(
            order_tags,
            dict,
        ):
            order_tags = None

        response = self.client.create_order(
            order_id=str(order_id),
            order_amount=amount,
            customer_name=str(customer_name),
            customer_phone=str(customer_phone),
            customer_email=(
                str(customer_email)
                if customer_email
                else None
            ),
            return_url=(
                str(return_url)
                if return_url
                else None
            ),
            notify_url=(
                str(notify_url)
                if notify_url
                else None
            ),
            order_note=(
                str(order_note)
                if order_note
                else None
            ),
            order_tags=order_tags,
            idempotency_key=payment_id,
        )

        normalized = CashfreeMapper.map_order_creation(
            response
        )

        provider_amount = normalized.get("amount")

        if (
            provider_amount is not None
            and provider_amount != amount
        ):
            raise PaymentProviderResponseError(
                "Cashfree returned an order amount that does not "
                "match the requested payment amount.",
                provider="cashfree",
                code="amount_mismatch",
            )

        provider_currency = normalized.get("currency")

        if (
            provider_currency
            and provider_currency.upper() != currency.upper()
        ):
            raise PaymentProviderResponseError(
                "Cashfree returned an unexpected currency.",
                provider="cashfree",
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

        payments = self.client.get_payments_for_order(
            order_id=provider_order_id
        )

        if not payments:
            raise PaymentProviderResponseError(
                "Cashfree returned no payment transactions "
                "for this order.",
                provider="cashfree",
                code="payment_not_found",
            )

        normalized_payments = [
            CashfreeMapper.map_payment(payment)
            for payment in payments
        ]

        if provider_payment_id:
            matching = [
                payment
                for payment in normalized_payments
                if payment.get("provider_payment_id")
                == provider_payment_id
            ]

            if not matching:
                raise PaymentProviderResponseError(
                    "Cashfree payment ID does not belong "
                    "to this order.",
                    provider="cashfree",
                    code="payment_order_mismatch",
                )

            return matching[0]

        # Prefer a successful transaction.
        successful = [
            payment
            for payment in normalized_payments
            if payment.get("status") == "succeeded"
        ]

        if successful:
            return successful[-1]

        # Otherwise prefer pending.
        pending = [
            payment
            for payment in normalized_payments
            if payment.get("status") == "pending"
        ]

        if pending:
            return pending[-1]

        # Otherwise return the most recent transaction.
        return normalized_payments[-1]

    # =========================================================
    # REFUND
    # =========================================================

    def refund_payment(
        self,
        *,
        provider_order_id: str,
        provider_payment_id: str | None = None,
        amount: Decimal | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:

        if amount is None:
            raise PaymentProviderResponseError(
                "Refund amount is required.",
                provider="cashfree",
                code="missing_refund_amount",
            )

        metadata = metadata or {}

        refund_id = metadata.get("refund_id")

        if not refund_id:
            raise PaymentProviderResponseError(
                "Refund ID is required for Cashfree refunds.",
                provider="cashfree",
                code="missing_refund_id",
            )

        reason = metadata.get("reason")

        refund_speed = (
            metadata.get("refund_speed")
            or "STANDARD"
        )

        response = self.client.create_refund(
            order_id=provider_order_id,
            refund_id=str(refund_id),
            refund_amount=amount,
            refund_note=(
                str(reason)
                if reason
                else None
            ),
            refund_speed=str(refund_speed),
            idempotency_key=str(refund_id),
        )

        normalized = CashfreeMapper.map_refund(
            response
        )

        provider_amount = normalized.get("amount")

        if (
            provider_amount is not None
            and provider_amount != amount
        ):
            raise PaymentProviderResponseError(
                "Cashfree returned a refund amount that does not "
                "match the requested refund amount.",
                provider="cashfree",
                code="refund_amount_mismatch",
            )

        normalized_payment_id = normalized.get(
            "provider_payment_id"
        )

        if (
            provider_payment_id
            and normalized_payment_id
            and normalized_payment_id != provider_payment_id
        ):
            raise PaymentProviderResponseError(
                "Cashfree refund belongs to a different payment.",
                provider="cashfree",
                code="refund_payment_mismatch",
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

        response = self.client.get_refund(
            order_id=provider_order_id,
            refund_id=provider_refund_id,
        )

        return CashfreeMapper.map_refund(
            response
        )

    # =========================================================
    # WEBHOOK VERIFICATION
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
                "Missing Cashfree webhook signature.",
                provider="cashfree",
                code="missing_signature",
            )

        if not timestamp:
            raise PaymentProviderSignatureError(
                "Missing Cashfree webhook timestamp.",
                provider="cashfree",
                code="missing_timestamp",
            )

        signed_payload = (
            timestamp.encode("utf-8")
            + payload
        )

        digest = hmac.new(
            settings.cashfree_webhook_secret.encode("utf-8"),
            signed_payload,
            hashlib.sha256,
        ).digest()

        expected_signature = base64.b64encode(
            digest
        ).decode("utf-8")

        if not hmac.compare_digest(
            expected_signature,
            signature,
        ):
            raise PaymentProviderSignatureError(
                "Invalid Cashfree webhook signature.",
                provider="cashfree",
                code="invalid_signature",
            )

        return True

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

    # =========================================================
    # WEBHOOK PARSING
    # =========================================================

    def parse_webhook(
        self,
        *,
        payload: dict[str, Any],
    ) -> dict[str, Any]:

        event_type = (
            payload.get("type")
            or payload.get("event")
            or payload.get("event_type")
        )

        data = payload.get("data") or {}

        if not isinstance(data, dict):
            raise PaymentProviderResponseError(
                "Invalid Cashfree webhook data.",
                provider="cashfree",
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

        # -----------------------------------------------------
        # Refund webhook
        # -----------------------------------------------------

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
                    refund_data.get("refund_currency")
                )
                or "INR"
            )

            provider_status = (
                CashfreeMapper._string(
                    refund_data.get("refund_status")
                )
            )

            event_id = (
                CashfreeMapper._string(
                    refund_data.get("refund_id")
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
                        refund_data.get("refund_arn")
                    )
                ),
                "failure_message": (
                    CashfreeMapper._string(
                        refund_data.get("refund_note")
                    )
                ),
                "raw_payload": payload,
            }

        # -----------------------------------------------------
        # Payment webhook
        # -----------------------------------------------------

        provider_order_id = (
            order_data.get("order_id")
            or payment_data.get("order_id")
            or payload.get("order_id")
        )

        provider_payment_id = (
            payment_data.get("cf_payment_id")
            or payment_data.get("payment_id")
        )

        amount = CashfreeMapper._decimal(
            payment_data.get("payment_amount")
            or order_data.get("order_amount")
        )

        currency = (
            CashfreeMapper._string(
                payment_data.get("payment_currency")
            )
            or CashfreeMapper._string(
                order_data.get("order_currency")
            )
            or "INR"
        )

        provider_status = (
            CashfreeMapper._string(
                payment_data.get("payment_status")
            )
            or CashfreeMapper._string(
                order_data.get("order_status")
            )
        )

        event_id = (
            CashfreeMapper._string(
                payment_data.get("cf_payment_id")
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
                or "payment.status"
            ),
            "entity_type": "payment",
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
            "provider_refund_id": None,
            "amount": amount,
            "currency": currency,
            "status": (
                CashfreeMapper.map_payment_status(
                    provider_status
                )
            ),
            "failure_code": (
                CashfreeMapper._string(
                    payment_data.get("payment_message")
                )
                if provider_status
                and provider_status.upper()
                in {"FAILED", "USER_DROPPED"}
                else None
            ),
            "failure_message": (
                CashfreeMapper._string(
                    payment_data.get("payment_message")
                )
                if provider_status
                and provider_status.upper()
                in {"FAILED", "USER_DROPPED"}
                else None
            ),
            "raw_payload": payload,
        }

    @staticmethod
    def _build_webhook_event_id(
        *,
        payload: dict[str, Any],
        entity_id: str | None,
        event_type: str | None,
    ) -> str:

        event_time = (
            payload.get("event_time")
            or payload.get("timestamp")
            or ""
        )

        source = "|".join(
            [
                str(event_type or ""),
                str(entity_id or ""),
                str(event_time),
            ]
        )

        return hashlib.sha256(
            source.encode("utf-8")
        ).hexdigest()