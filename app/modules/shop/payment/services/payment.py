from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from fastapi import HTTPException

from app.modules.shop.order.repositories.order import OrderRepository
from app.modules.shop.order.services.order import OrderService

from app.modules.shop.payment.models.payment import Payment
from app.modules.shop.payment.models.payment_attempt import PaymentAttempt
from app.modules.shop.payment.models.payment_event import PaymentEvent
from app.modules.shop.payment.models.webhook_event import WebhookEvent
from app.modules.shop.payment.repositories.refund import RefundRepository

from app.modules.shop.payment.providers.exceptions import (
    PaymentProviderError,
)

from app.modules.shop.payment.repositories.payment import PaymentRepository
from app.modules.shop.payment.router.payment_router import PaymentRouter
from app.modules.shop.payment.schemas.payment import VerifyPaymentRequest

from app.modules.shop.payment.services.payment_state import (
    PaymentStatus,
    transition_payment_status,
)
from app.modules.shop.payment.services.refund import RefundService


class PaymentService:

    def __init__(self, db):
        self.db = db

        self.payment_repository = PaymentRepository(db)

        self.order_repository = OrderRepository(db)

        self.payment_router = PaymentRouter()

    # =========================================================
    # HELPERS
    # =========================================================

    @staticmethod
    def _json_safe(data):

        if isinstance(data, Decimal):
            return str(data)

        if isinstance(data, dict):
            return {
                key: PaymentService._json_safe(value)
                for key, value in data.items()
            }

        if isinstance(data, list):
            return [
                PaymentService._json_safe(value)
                for value in data
            ]

        if isinstance(data, tuple):
            return [
                PaymentService._json_safe(value)
                for value in data
            ]

        return data

    # =========================================================
    # CREATE PAYMENT
    # =========================================================

    def create_payment(
        self,
        order_public_id: str,
        customer,
        provider_name: str = "cashfree",
    ) -> Payment:

        # -----------------------------------------------------
        # 1. Find order
        # -----------------------------------------------------

        order = self.order_repository.get_by_public_id(
            public_id=order_public_id,
            customer_id=customer.id,
        )

        if order is None:
            raise HTTPException(
                status_code=404,
                detail="Order not found.",
            )

        # -----------------------------------------------------
        # 2. One payment per order
        # -----------------------------------------------------

        existing_payment = self.payment_repository.get_by_order_id(
            order.id
        )

        if existing_payment is not None:
            return existing_payment

        # -----------------------------------------------------
        # 3. Validate order status
        # -----------------------------------------------------

        if order.status != "pending_payment":
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Payment cannot be created for an order "
                    f"in '{order.status}' status."
                ),
            )

        # -----------------------------------------------------
        # 4. Validate amount
        # -----------------------------------------------------

        amount = Decimal(str(order.total_amount))

        if amount <= Decimal("0.00"):
            raise HTTPException(
                status_code=400,
                detail="Order amount must be greater than zero.",
            )

        # -----------------------------------------------------
        # 5. Resolve provider
        # -----------------------------------------------------

        provider = self.payment_router.get_provider(
            provider_name
        )

        # -----------------------------------------------------
        # 6. Create local payment
        # -----------------------------------------------------

        payment = Payment(
            public_id=str(uuid4()),
            order_id=order.id,
            customer_id=customer.id,
            amount=amount,
            currency="INR",
            provider=provider.provider_name,
            provider_order_id=None,
            provider_payment_id=None,
            status=PaymentStatus.CREATED,
        )

        self.payment_repository.create(payment)

        # -----------------------------------------------------
        # 7. Create payment attempt
        # -----------------------------------------------------

        attempt_number = (
            self.payment_repository.get_next_attempt_number(
                payment.id
            )
        )

        attempt = PaymentAttempt(
            public_id=str(uuid4()),
            payment_id=payment.id,
            attempt_number=attempt_number,
            provider=provider.provider_name,
            amount=payment.amount,
            currency=payment.currency,
            status=PaymentStatus.CREATED,
            provider_order_id=None,
            provider_payment_id=None,
            failure_code=None,
            failure_message=None,
        )

        self.payment_repository.create_attempt(attempt)

        # -----------------------------------------------------
        # 8. Create payment event
        # -----------------------------------------------------

        self.payment_repository.create_event(
            PaymentEvent(
                public_id=str(uuid4()),
                payment_id=payment.id,
                attempt_id=attempt.id,
                event_type="payment_created",
                status=PaymentStatus.CREATED,
                message="Payment created.",
                event_data={
                    "order_public_id": order.public_id,
                    "order_number": order.order_number,
                    "provider": provider.provider_name,
                    "amount": str(payment.amount),
                    "currency": payment.currency,
                },
            )
        )

        # -----------------------------------------------------
        # 9. Create provider order
        # -----------------------------------------------------

        try:

            provider_result = provider.create_payment_order(
                payment_id=payment.public_id,
                amount=payment.amount,
                currency=payment.currency,
                metadata={
                    "order_public_id": order.public_id,
                    "order_number": order.order_number,
                    "customer_id": customer.id,
                    "customer_phone": customer.phone_number,
                    "customer_email": customer.email,
                },
            )

        except PaymentProviderError as exc:

            attempt.status = PaymentStatus.FAILED

            attempt.failure_code = exc.code

            attempt.failure_message = exc.message

            self.payment_repository.create_event(
                PaymentEvent(
                    public_id=str(uuid4()),
                    payment_id=payment.id,
                    attempt_id=attempt.id,
                    event_type="provider_order_failed",
                    status=PaymentStatus.FAILED,
                    message=exc.message,
                    event_data={
                        "provider": provider.provider_name,
                        "error_code": exc.code,
                    },
                )
            )

            self.payment_repository.save()

            raise HTTPException(
                status_code=502,
                detail=(
                    "Payment provider could not create "
                    "the payment order."
                ),
            ) from exc

        # -----------------------------------------------------
        # 10. Save provider order ID
        # -----------------------------------------------------

        provider_order_id = provider_result[
            "provider_order_id"
        ]

        payment.provider_order_id = provider_order_id
        payment.payment_session_id = provider_result.get(
            "payment_session_id"
        )

        attempt.provider_order_id = provider_order_id

        # -----------------------------------------------------
        # 11. Move payment to pending
        # -----------------------------------------------------

        transition_payment_status(
            payment,
            PaymentStatus.PENDING,
        )

        attempt.status = PaymentStatus.PENDING

        # -----------------------------------------------------
        # 12. Create provider order event
        # -----------------------------------------------------

        self.payment_repository.create_event(
            PaymentEvent(
                public_id=str(uuid4()),
                payment_id=payment.id,
                attempt_id=attempt.id,
                event_type="provider_order_created",
                status=PaymentStatus.PENDING,
                message="Payment provider order created.",
                event_data={
                    "provider": provider.provider_name,
                    "provider_order_id": provider_order_id,
                    "provider_status": provider_result.get(
                        "status"
                    ),
                    "amount": str(payment.amount),
                    "currency": payment.currency,
                },
            )
        )

        self.payment_repository.save()

        return payment

    # =========================================================
    # VERIFY PAYMENT
    # =========================================================

    def verify_payment(
        self,
        *,
        payment_public_id: str,
        request: VerifyPaymentRequest,
        customer,
    ):

        # -----------------------------------------------------
        # 1. Find payment
        # -----------------------------------------------------

        payment = self.payment_repository.get_by_public_id(
            public_id=payment_public_id,
            customer_id=customer.id,
        )

        if payment is None:
            raise HTTPException(
                status_code=404,
                detail="Payment not found.",
            )

        # -----------------------------------------------------
        # 2. Validate provider
        # -----------------------------------------------------

        if payment.provider is None:
            raise HTTPException(
                status_code=400,
                detail="Payment provider is not configured.",
            )

        # -----------------------------------------------------
        # 3. Validate provider order
        # -----------------------------------------------------

        if payment.provider_order_id is None:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Payment provider order has not "
                    "been created."
                ),
            )

        # -----------------------------------------------------
        # 4. Never trust frontend order ID
        # -----------------------------------------------------

        if (
            request.razorpay_order_id
            != payment.provider_order_id
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Razorpay order ID does not match "
                    "the payment."
                ),
            )

        # -----------------------------------------------------
        # 5. Resolve provider
        # -----------------------------------------------------

        provider = self.payment_router.get_provider(
            payment.provider
        )

        # -----------------------------------------------------
        # 6. Verify payment with provider
        # -----------------------------------------------------

        try:

            verification = provider.verify_payment(
                provider_order_id=payment.provider_order_id,
                provider_payment_id=(
                    request.razorpay_payment_id
                ),
                signature=request.razorpay_signature,
            )

        except PaymentProviderError as exc:

            raise HTTPException(
                status_code=400,
                detail="Payment verification failed.",
            ) from exc

        except Exception as exc:

            raise HTTPException(
                status_code=400,
                detail="Payment verification failed.",
            ) from exc

        # -----------------------------------------------------
        # 7. Extract provider values
        # -----------------------------------------------------

        provider_payment_id = verification.get(
            "provider_payment_id"
        )

        provider_order_id = verification.get(
            "provider_order_id"
        )

        provider_amount = verification.get(
            "amount"
        )

        provider_currency = verification.get(
            "currency"
        )

        provider_status = verification.get(
            "status"
        )

        # -----------------------------------------------------
        # 8. Validate payment ID
        # -----------------------------------------------------

        if (
            provider_payment_id
            != request.razorpay_payment_id
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Verified payment ID does not "
                    "match the request."
                ),
            )

        # -----------------------------------------------------
        # 9. Validate order ID
        # -----------------------------------------------------

        if (
            provider_order_id
            != payment.provider_order_id
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Verified order ID does not "
                    "match the payment."
                ),
            )

        # -----------------------------------------------------
        # 10. Validate amount
        # -----------------------------------------------------

        if (
            Decimal(str(provider_amount))
            != Decimal(str(payment.amount))
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Payment amount does not match "
                    "the order amount."
                ),
            )

        # -----------------------------------------------------
        # 11. Validate currency
        # -----------------------------------------------------

        if (
            provider_currency.upper()
            != payment.currency.upper()
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Payment currency does not match "
                    "the order currency."
                ),
            )

        # -----------------------------------------------------
        # 12. Get latest attempt
        # -----------------------------------------------------

        attempt = self.payment_repository.get_latest_attempt(
            payment.id
        )

        if attempt is None:
            raise HTTPException(
                status_code=500,
                detail="Payment attempt not found.",
            )

        # -----------------------------------------------------
        # 13. Save provider payment ID
        # -----------------------------------------------------

        attempt.provider_payment_id = (
            provider_payment_id
        )

        payment.provider_payment_id = (
            provider_payment_id
        )

        # =====================================================
        # CAPTURED
        # =====================================================

        if provider_status == "captured":

            already_succeeded = (
                payment.status
                == PaymentStatus.SUCCEEDED
            )

            # -------------------------------------------------
            # Move payment to succeeded
            # -------------------------------------------------

            if not already_succeeded:

                transition_payment_status(
                    payment,
                    PaymentStatus.SUCCEEDED,
                )

            attempt.status = PaymentStatus.SUCCEEDED

            # -------------------------------------------------
            # Avoid duplicate success events
            # -------------------------------------------------

            if not already_succeeded:

                self.payment_repository.create_event(
                    PaymentEvent(
                        public_id=str(uuid4()),
                        payment_id=payment.id,
                        attempt_id=attempt.id,
                        event_type="payment_succeeded",
                        status=PaymentStatus.SUCCEEDED,
                        message=(
                            "Razorpay payment verified "
                            "successfully."
                        ),
                        event_data=self._json_safe(
                            verification
                        ),
                    )
                )

            # -------------------------------------------------
            # Find order
            # -------------------------------------------------

            order = self.order_repository.get_by_id(
                payment.order_id
            )

            if order is None:
                raise HTTPException(
                    status_code=500,
                    detail=(
                        "Order not found for payment."
                    ),
                )

            # -------------------------------------------------
            # Idempotent order payment
            # -------------------------------------------------

            if order.status != "paid":

                OrderService(self.db).mark_order_paid(
                    order
                )

        # =====================================================
        # AUTHORIZED
        # =====================================================

        elif provider_status == "authorized":

            already_authorized = (
                payment.status
                == PaymentStatus.AUTHORIZED
            )

            if not already_authorized:

                transition_payment_status(
                    payment,
                    PaymentStatus.AUTHORIZED,
                )

            attempt.status = PaymentStatus.AUTHORIZED

            if not already_authorized:

                self.payment_repository.create_event(
                    PaymentEvent(
                        public_id=str(uuid4()),
                        payment_id=payment.id,
                        attempt_id=attempt.id,
                        event_type="payment_authorized",
                        status=PaymentStatus.AUTHORIZED,
                        message=(
                            "Razorpay payment was "
                            "authorized."
                        ),
                        event_data=self._json_safe(
                            verification
                        ),
                    )
                )

        # =====================================================
        # FAILED
        # =====================================================

        elif provider_status == "failed":

            # -------------------------------------------------
            # Never downgrade a successful payment
            # -------------------------------------------------

            if payment.status in {
                PaymentStatus.SUCCEEDED,
                PaymentStatus.REFUNDED,
                PaymentStatus.PARTIALLY_REFUNDED,
            }:

                self.payment_repository.create_event(
                    PaymentEvent(
                        public_id=str(uuid4()),
                        payment_id=payment.id,
                        attempt_id=attempt.id,
                        event_type="payment_failed_ignored",
                        status=payment.status,
                        message=(
                            "Late Razorpay failure "
                            "status ignored because "
                            f"payment is already "
                            f"'{payment.status}'."
                        ),
                        event_data=self._json_safe(
                            verification
                        ),
                    )
                )

            else:

                already_failed = (
                    payment.status
                    == PaymentStatus.FAILED
                )

                if not already_failed:

                    transition_payment_status(
                        payment,
                        PaymentStatus.FAILED,
                    )

                attempt.status = PaymentStatus.FAILED

                if not already_failed:

                    self.payment_repository.create_event(
                        PaymentEvent(
                            public_id=str(uuid4()),
                            payment_id=payment.id,
                            attempt_id=attempt.id,
                            event_type="payment_failed",
                            status=PaymentStatus.FAILED,
                            message=(
                                "Razorpay payment failed."
                            ),
                            event_data=self._json_safe(
                                verification
                            ),
                        )
                    )

        # =====================================================
        # UNKNOWN PROVIDER STATUS
        # =====================================================

        else:

            self.payment_repository.create_event(
                PaymentEvent(
                    public_id=str(uuid4()),
                    payment_id=payment.id,
                    attempt_id=attempt.id,
                    event_type="payment_status_checked",
                    status=payment.status,
                    message=(
                        "Razorpay payment status checked: "
                        f"{provider_status}."
                    ),
                    event_data=self._json_safe(
                        verification
                    ),
                )
            )

        # -----------------------------------------------------
        # Save
        # -----------------------------------------------------

        self.payment_repository.save()

        return payment

        # =========================================================
    # RAZORPAY REFUND WEBHOOK
    # =========================================================

        # =========================================================
    # RAZORPAY REFUND WEBHOOK
    # =========================================================

    def _process_refund_webhook(
        self,
        *,
        webhook_event: WebhookEvent,
        normalized: dict,
    ) -> None:

        event_type = normalized["event_type"]

        provider_refund_id = normalized[
            "provider_refund_id"
        ]

        provider_payment_id = normalized[
            "provider_payment_id"
        ]

        amount = Decimal(
            str(normalized["amount"])
        )

        currency = normalized["currency"]

        provider_status = normalized.get(
            "provider_status"
        )

        # -----------------------------------------------------
        # 1. Find local refund
        # -----------------------------------------------------

        refund_repository = RefundRepository(
            self.db
        )

        refund = (
            refund_repository
            .get_by_provider_refund_id(
                provider_refund_id
            )
        )

        if refund is None:

            webhook_event.status = "failed"

            webhook_event.error_message = (
                "Refund not found for Razorpay "
                f"refund '{provider_refund_id}'."
            )

            webhook_event.processed_at = (
                datetime.now(timezone.utc)
            )

            self.payment_repository.save_webhook_event()

            raise HTTPException(
                status_code=400,
                detail=(
                    "Refund not found for Razorpay "
                    "refund."
                ),
            )

        # -----------------------------------------------------
        # 2. Find payment
        # -----------------------------------------------------

        payment = (
            self.payment_repository
            .get_by_id(refund.payment_id)
        )

        if payment is None:

            webhook_event.status = "failed"

            webhook_event.error_message = (
                "Payment not found for refund."
            )

            webhook_event.processed_at = (
                datetime.now(timezone.utc)
            )

            self.payment_repository.save_webhook_event()

            raise HTTPException(
                status_code=400,
                detail="Payment not found for refund.",
            )

        # -----------------------------------------------------
        # 3. Validate provider payment ID
        # -----------------------------------------------------

        if (
            payment.provider_payment_id
            != provider_payment_id
        ):

            webhook_event.status = "failed"

            webhook_event.error_message = (
                "Refund webhook payment ID does not "
                "match the local payment."
            )

            webhook_event.processed_at = (
                datetime.now(timezone.utc)
            )

            self.payment_repository.save_webhook_event()

            raise HTTPException(
                status_code=400,
                detail=(
                    "Refund webhook payment ID does "
                    "not match the local payment."
                ),
            )

        # -----------------------------------------------------
        # 4. Validate amount
        # -----------------------------------------------------

        if Decimal(str(refund.amount)) != amount:

            webhook_event.status = "failed"

            webhook_event.error_message = (
                "Refund webhook amount does not "
                "match the local refund."
            )

            webhook_event.processed_at = (
                datetime.now(timezone.utc)
            )

            self.payment_repository.save_webhook_event()

            raise HTTPException(
                status_code=400,
                detail=(
                    "Refund webhook amount does not "
                    "match the local refund."
                ),
            )

        # -----------------------------------------------------
        # 5. Validate currency
        # -----------------------------------------------------

        if (
            refund.currency.upper()
            != currency.upper()
        ):

            webhook_event.status = "failed"

            webhook_event.error_message = (
                "Refund webhook currency does not "
                "match the local refund."
            )

            webhook_event.processed_at = (
                datetime.now(timezone.utc)
            )

            self.payment_repository.save_webhook_event()

            raise HTTPException(
                status_code=400,
                detail=(
                    "Refund webhook currency does "
                    "not match the local refund."
                ),
            )

        # -----------------------------------------------------
        # 6. Save provider response
        # -----------------------------------------------------

        refund.provider_response = (
            normalized["raw_payload"]
        )

        # -----------------------------------------------------
        # 7. Process refund status
        # -----------------------------------------------------

        if provider_status in {
            "processed",
            "succeeded",
            "success",
            "completed",
        }:

            refund.status = "succeeded"

        elif provider_status in {
            "failed",
            "failure",
        }:

            refund.status = "failed"

            refund.failure_code = (
                normalized.get("failure_code")
            )

            refund.failure_message = (
                normalized.get("failure_message")
            )

        else:

            refund.status = "pending"

        # -----------------------------------------------------
        # 8. Synchronize payment state
        # -----------------------------------------------------

        refund_service = RefundService(self.db)

        refund_service._sync_payment_state_after_refund(
            payment=payment,
            refund=refund,
        )

        # -----------------------------------------------------
        # 9. Create payment event
        # -----------------------------------------------------

        self.payment_repository.create_event(
            PaymentEvent(
                public_id=str(uuid4()),
                payment_id=payment.id,
                attempt_id=None,
                event_type=(
                    f"refund_webhook_{event_type}"
                ),
                status=refund.status,
                message=(
                    "Razorpay refund webhook processed."
                ),
                event_data=self._json_safe(
                    {
                        "provider_refund_id":
                            provider_refund_id,
                        "provider_payment_id":
                            provider_payment_id,
                        "amount": amount,
                        "currency": currency,
                        "provider_status":
                            provider_status,
                    }
                ),
            )
        )

        # -----------------------------------------------------
        # 10. Mark webhook processed
        # -----------------------------------------------------

        webhook_event.status = "processed"

        webhook_event.error_message = None

        webhook_event.processed_at = (
            datetime.now(timezone.utc)
        )

        self.payment_repository.save()
    # =========================================================
    # RAZORPAY WEBHOOK
    # =========================================================

    def process_razorpay_webhook(
        self,
        *,
        webhook_event: WebhookEvent,
        normalized: dict,
    ) -> None:

        event_type = normalized["event_type"]
        if normalized.get("entity_type") == "refund":
            self._process_refund_webhook(
                webhook_event=webhook_event,
                normalized=normalized,
            )
            return

        provider_payment_id = normalized[
            "provider_payment_id"
        ]

        provider_order_id = normalized[
            "provider_order_id"
        ]

        amount = Decimal(
            str(normalized["amount"])
        )

        currency = normalized["currency"]

        # -----------------------------------------------------
        # 1. Find payment
        # -----------------------------------------------------

        payment = (
            self.payment_repository
            .get_by_provider_order_id(
                provider_order_id
            )
        )

        if payment is None:

            webhook_event.status = "ignored"

            webhook_event.error_message = (
                "Payment not found for Razorpay "
                f"order '{provider_order_id}'."
            )

            webhook_event.processed_at = (
                datetime.now(timezone.utc)
            )

            self.payment_repository.save_webhook_event()

            return

        # -----------------------------------------------------
        # 2. Validate amount
        # -----------------------------------------------------

        if payment.amount != amount:

            webhook_event.status = "failed"

            webhook_event.error_message = (
                "Webhook amount does not match "
                "payment amount."
            )

            webhook_event.processed_at = (
                datetime.now(timezone.utc)
            )

            self.payment_repository.save_webhook_event()

            raise HTTPException(
                status_code=400,
                detail=(
                    "Webhook amount does not match "
                    "payment amount."
                ),
            )

        # -----------------------------------------------------
        # 3. Validate currency
        # -----------------------------------------------------

        if (
            payment.currency.upper()
            != currency.upper()
        ):

            webhook_event.status = "failed"

            webhook_event.error_message = (
                "Webhook currency does not match "
                "payment currency."
            )

            webhook_event.processed_at = (
                datetime.now(timezone.utc)
            )

            self.payment_repository.save_webhook_event()

            raise HTTPException(
                status_code=400,
                detail=(
                    "Webhook currency does not match "
                    "payment currency."
                ),
            )

        # -----------------------------------------------------
        # 4. Get latest attempt
        # -----------------------------------------------------

        attempt = (
            self.payment_repository
            .get_latest_attempt(payment.id)
        )

        if attempt is None:

            webhook_event.status = "failed"

            webhook_event.error_message = (
                "Payment attempt not found."
            )

            webhook_event.processed_at = (
                datetime.now(timezone.utc)
            )

            self.payment_repository.save_webhook_event()

            raise HTTPException(
                status_code=400,
                detail="Payment attempt not found.",
            )

        # -----------------------------------------------------
        # 5. Prevent conflicting payment IDs
        # -----------------------------------------------------

        if (
            payment.provider_payment_id is not None
            and payment.provider_payment_id
            != provider_payment_id
        ):

            webhook_event.status = "failed"

            webhook_event.error_message = (
                "Webhook payment ID does not match "
                "the existing payment."
            )

            webhook_event.processed_at = (
                datetime.now(timezone.utc)
            )

            self.payment_repository.save_webhook_event()

            raise HTTPException(
                status_code=400,
                detail=(
                    "Webhook payment ID does not match "
                    "the existing payment."
                ),
            )

        attempt.provider_payment_id = (
            provider_payment_id
        )

        # =====================================================
        # PAYMENT CAPTURED
        # =====================================================

        if event_type == "payment.captured":

            already_succeeded = (
                payment.status
                == PaymentStatus.SUCCEEDED
            )

            # -------------------------------------------------
            # Move payment to succeeded
            # -------------------------------------------------

            if payment.status not in {
                PaymentStatus.SUCCEEDED,
                PaymentStatus.REFUNDED,
                PaymentStatus.PARTIALLY_REFUNDED,
            }:

                transition_payment_status(
                    payment,
                    PaymentStatus.SUCCEEDED,
                )

            # -------------------------------------------------
            # Save provider payment ID
            # -------------------------------------------------

            payment.provider_payment_id = (
                provider_payment_id
            )

            attempt.provider_payment_id = (
                provider_payment_id
            )

            attempt.status = PaymentStatus.SUCCEEDED

            # -------------------------------------------------
            # Avoid duplicate success events
            # -------------------------------------------------

            if not already_succeeded:

                self.payment_repository.create_event(
                    PaymentEvent(
                        public_id=str(uuid4()),
                        payment_id=payment.id,
                        attempt_id=attempt.id,
                        event_type="payment_succeeded",
                        status=PaymentStatus.SUCCEEDED,
                        message=(
                            "Payment confirmed by "
                            "Razorpay webhook."
                        ),
                        event_data=normalized[
                            "raw_payload"
                        ],
                    )
                )

            # -------------------------------------------------
            # Find order
            # -------------------------------------------------

            order = self.order_repository.get_by_id(
                payment.order_id
            )

            if order is None:

                webhook_event.status = "failed"

                webhook_event.error_message = (
                    "Order not found for payment."
                )

                webhook_event.processed_at = (
                    datetime.now(timezone.utc)
                )

                self.payment_repository.save_webhook_event()

                raise HTTPException(
                    status_code=500,
                    detail=(
                        "Order not found for payment."
                    ),
                )

            # -------------------------------------------------
            # Idempotent order payment
            # -------------------------------------------------

            if order.status != "paid":

                OrderService(self.db).mark_order_paid(
                    order
                )

        # =====================================================
        # PAYMENT FAILED
        # =====================================================

        elif event_type == "payment.failed":

            # -------------------------------------------------
            # Never downgrade successful payment
            # -------------------------------------------------

            if payment.status in {
                PaymentStatus.SUCCEEDED,
                PaymentStatus.REFUNDED,
                PaymentStatus.PARTIALLY_REFUNDED,
            }:

                self.payment_repository.create_event(
                    PaymentEvent(
                        public_id=str(uuid4()),
                        payment_id=payment.id,
                        attempt_id=attempt.id,
                        event_type="payment_failed_ignored",
                        status=payment.status,
                        message=(
                            "Late Razorpay failure "
                            "webhook ignored because "
                            f"payment is already "
                            f"'{payment.status}'."
                        ),
                        event_data=normalized[
                            "raw_payload"
                        ],
                    )
                )

            else:

                already_failed = (
                    payment.status
                    == PaymentStatus.FAILED
                )

                if not already_failed:

                    transition_payment_status(
                        payment,
                        PaymentStatus.FAILED,
                    )

                attempt.status = PaymentStatus.FAILED

                if not already_failed:

                    self.payment_repository.create_event(
                        PaymentEvent(
                            public_id=str(uuid4()),
                            payment_id=payment.id,
                            attempt_id=attempt.id,
                            event_type="payment_failed",
                            status=PaymentStatus.FAILED,
                            message=(
                                "Payment failed according "
                                "to Razorpay webhook."
                            ),
                            event_data=normalized[
                                "raw_payload"
                            ],
                        )
                    )

        # =====================================================
        # UNSUPPORTED EVENT
        # =====================================================

        else:

            webhook_event.status = "failed"

            webhook_event.error_message = (
                "Unsupported Razorpay webhook event: "
                f"{event_type}"
            )

            webhook_event.processed_at = (
                datetime.now(timezone.utc)
            )

            self.payment_repository.save_webhook_event()

            raise HTTPException(
                status_code=400,
                detail=(
                    "Unsupported Razorpay webhook event: "
                    f"{event_type}"
                ),
            )

        # =====================================================
        # WEBHOOK SUCCESS
        # =====================================================

        webhook_event.status = "processed"

        webhook_event.error_message = None

        webhook_event.processed_at = (
            datetime.now(timezone.utc)
        )

        self.payment_repository.save()