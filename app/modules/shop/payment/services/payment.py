from datetime import datetime, timezone

from decimal import Decimal

from uuid import uuid4

from app.modules.admin.notifications.services.notification import (

    NotificationService,

)
import logging

from app.core.email import EmailService
from app.modules.shop.customer.services.email_templates import (
    build_order_confirmation_email,
)

from app.modules.affiliate.models.affiliate_attribution import (
    AffiliateAttribution,
)
from app.modules.affiliate.services.comimsion_service import (
    CommissionService,
)
logger = logging.getLogger(__name__)
from sqlalchemy import select

from app.modules.admin.auth.models.admin_user import AdminUser

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


        def _send_order_confirmation_email(self, *, order, payment) -> None:
            # Prevent duplicate confirmation emails.
            if order.confirmation_email_sent_at is not None:
                return

            if not order.customer_email:
                logger.warning(
                    "Order confirmation email skipped: no customer email for %s",
                    order.order_number,
                )
                return

            try:
                html = build_order_confirmation_email(order, payment)

                EmailService().send_email(
                    to=order.customer_email,
                    subject=f"Order confirmed — {order.order_number}",
                    html=html,
                )

                order.confirmation_email_sent_at = datetime.now(timezone.utc)

                logger.info(
                    "Order confirmation email sent for %s",
                    order.order_number,
                )

            except Exception:
                # Email failure must not turn a successful payment into a failure.
                logger.exception(
                    "Failed to send order confirmation email for %s",
                    order.order_number,
                )

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

        existing_payment = (

            self.payment_repository.get_by_order_id(

                order.id

            )

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

                    "customer_name": (

                        getattr(customer, "name", None)

                        or getattr(customer, "full_name", None)

                        or "EnergyMax Customer"

                    ),

                    "customer_phone": customer.phone,

                    "customer_email": getattr(

                        customer,

                        "email",

                        None,

                    ),

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

                detail={

                    "message": (

                        "Payment provider could not create "

                        "the payment order."

                    ),

                    "provider": provider.provider_name,

                    "error_code": exc.code,

                    "provider_error": exc.message,

                },

            ) from exc

        # -----------------------------------------------------

        # 10. Save provider order ID

        # -----------------------------------------------------

        provider_order_id = provider_result[

            "provider_order_id"

        ]

        payment.provider_order_id = provider_order_id

        payment.payment_session_id = (

            provider_result.get("payment_session_id")

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

                    "payment_session_id": provider_result.get(

                        "payment_session_id"

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

        # 4. Provider order ID comes from our database

        # -----------------------------------------------------

        provider_order_id = payment.provider_order_id

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

                provider_order_id=provider_order_id,

                provider_payment_id=(

                    request.provider_payment_id

                ),

            )

        except PaymentProviderError as exc:

            raise HTTPException(

                status_code=400,

                detail=exc.message,

            ) from exc

        except Exception as exc:

            import traceback

            print("========================================")

            print("PAYMENT SERVICE VERIFY ERROR")

            print("ERROR TYPE:", type(exc).__name__)

            print("ERROR:", str(exc))

            traceback.print_exc()

            print("========================================")

            raise HTTPException(

                status_code=500,

                detail="Payment verification failed. Please try again or contact support.",

            ) from exc

        # -----------------------------------------------------

        # 7. Extract provider values

        # -----------------------------------------------------

        verified_payment_id = verification.get(

            "provider_payment_id"

        )

        verified_order_id = verification.get(

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

        # 8. Validate provider order ID

        # -----------------------------------------------------

        if verified_order_id != payment.provider_order_id:

            raise HTTPException(

                status_code=400,

                detail=(

                    "Verified provider order ID does not "

                    "match the payment."

                ),

            )

        # -----------------------------------------------------

        # 9. Validate payment ID when supplied

        # -----------------------------------------------------

        if (

            request.provider_payment_id

            and verified_payment_id

            and verified_payment_id

            != request.provider_payment_id

        ):

            raise HTTPException(

                status_code=400,

                detail=(

                    "Verified payment ID does not "

                    "match the request."

                ),

            )

        # -----------------------------------------------------

        # 10. Validate amount when provider returns it

        # -----------------------------------------------------

        if provider_amount is not None:

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

        # 11. Validate currency when provider returns it

        # -----------------------------------------------------

        if provider_currency is not None:

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

        attempt = None

        if payment.provider_order_id:

            attempt = (

                self.payment_repository

                .get_attempt_by_provider_order_id(
                    payment_id=payment.id,
                    provider_order_id=payment.provider_order_id
                )

            )

        if attempt is None:

            raise HTTPException(

                status_code=500,

                detail="Payment attempt not found.",

            )

        # -----------------------------------------------------

        # 13. Save provider payment ID when available

        # -----------------------------------------------------

        if verified_payment_id:

            attempt.provider_payment_id = (

                verified_payment_id

            )

            payment.provider_payment_id = (

                verified_payment_id

            )

        # =====================================================

        # SUCCEEDED

        # =====================================================

        if provider_status in {

            "succeeded",

            "captured",

            "success",

            "completed",

        }:

            if not verified_payment_id:

                raise HTTPException(

                    status_code=400,

                    detail=(

                        "Provider reported successful payment "

                        "without a payment ID."

                    ),

                )

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

                            "Cashfree payment verified "

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

                    detail="Order not found for payment.",

                )

            # -------------------------------------------------

            # Idempotent order payment

            # -------------------------------------------------

            if order.status != "paid":

                OrderService(self.db).mark_order_paid(

                    order

                )
            self._send_order_confirmation_email(order=order, payment=payment,
                                                )

        if not already_succeeded:

            notification_service = NotificationService(self.db)

            active_admins = self.db.scalars(

                select(AdminUser).where(

                    AdminUser.is_active == True

                )

            ).all()

            for admin in active_admins:

                notification_service.notify_payment_success(

                    admin_user_id=admin.id,

                    order_public_id=order.public_id,

                    payment_public_id=payment.public_id,

                    order_number=order.order_number,

                    amount=str(payment.amount),

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

                            "Cashfree payment was "

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

                            "Late Cashfree failure "

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

                                "Cashfree payment failed."

                            ),

                            event_data=self._json_safe(

                                verification

                            ),

                        )

                    )

        # =====================================================

        # PENDING / PROCESSING

        # =====================================================

            # Release active reservations after a verified failure, unless already paid.
            order = self.order_repository.get_by_id(payment.order_id)
            if order is not None and order.status != "paid":
                OrderService(self.db).release_order_reservations(order)

        elif provider_status in {

            None,

            "pending",

            "processing",

        }:

            if payment.status == PaymentStatus.CREATED:

                transition_payment_status(

                    payment,

                    PaymentStatus.PENDING,

                )

            attempt.status = PaymentStatus.PENDING

            self.payment_repository.create_event(

                PaymentEvent(

                    public_id=str(uuid4()),

                    payment_id=payment.id,

                    attempt_id=attempt.id,

                    event_type="payment_status_checked",

                    status=PaymentStatus.PENDING,

                    message=(

                        "Cashfree payment is still pending."

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

                        "Cashfree payment status checked: "

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

    # CASHFREE REFUND WEBHOOK

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

                "Refund not found for Cashfree "

                f"refund '{provider_refund_id}'."

            )

            webhook_event.processed_at = (

                datetime.now(timezone.utc)

            )

            self.payment_repository.save_webhook_event()

            raise HTTPException(

                status_code=400,

                detail=(

                    "Refund not found for Cashfree "

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

        refund_service = RefundService(

            self.db

        )

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

                    "Cashfree refund webhook processed."

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

    # CASHFREE WEBHOOK

    # =========================================================

    def process_cashfree_webhook(

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

                "Payment not found for Cashfree "

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

            .get_attempt_by_provider_order_id(

                payment_id=payment.id,

                provider_order_id=provider_order_id

            )

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

        # -----------------------------------------------------

        # 6. Save provider payment ID

        # -----------------------------------------------------

        payment.provider_payment_id = (

            provider_payment_id

        )

        attempt.provider_payment_id = (

            provider_payment_id

        )

        # =====================================================

        # PAYMENT SUCCEEDED

        # =====================================================

        if event_type == "payment.succeeded":

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

                            "Cashfree webhook."

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

            # AFFILIATE COMMISSION — VERIFIED CASHFREE PAYMENT ONLY

            attribution_id = self.db.scalar(
                select(AffiliateAttribution.id).where(
                    AffiliateAttribution.order_id == order.id

                )
            )

            if attribution_id is not None:
                    # Calculate the eligible amount using trusted server-side
                    # order values. Exclude discounts, shipping and tax.
                subtotal = Decimal(str(order.subtotal or 0))
                discount = Decimal(str(order.discount_amount or 0))

                eligible_amount = max(
                    Decimal("0.00"),
                    subtotal - discount,
                ).quantize(Decimal("0.01"))

                if eligible_amount > Decimal("0.00"):
                    CommissionService(self.db).create_commission(
                        order_id=order.id,
                        eligible_amount=eligible_amount,
                        idempotency_key=f"affiliate-commission-order-{order.id}",
                        currency=str(payment.currency or "INR"),
                        description=(
                            f"Affiliate commission for paid order "
                            f"{order.order_number}"
                        ),
                    )

        # =====================================================

        # PAYMENT FAILED

        # =====================================================

        
        elif event_type == "payment.failed":
            # Never downgrade a successful or refunded payment.
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
                            "Late Cashfree failure webhook ignored "
                            "because payment is already successful "
                            "or refunded."
                        ),
                        event_data=normalized["raw_payload"],
                    )
                )
            else:
                already_failed = (
                    payment.status == PaymentStatus.FAILED
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
                                "Payment failed according to "
                                "Cashfree webhook."
                            ),
                            event_data=normalized["raw_payload"],
                        )
                    )

                # Release inventory only for an accepted failure.
                order = self.order_repository.get_by_id(
                    payment.order_id
                )
                if order is not None and order.status != "paid":
                    OrderService(
                        self.db
                    ).release_order_reservations(order)


        # =====================================================

        # UNSUPPORTED EVENT

        # =====================================================

        else:

            webhook_event.status = "failed"

            webhook_event.error_message = (

                "Unsupported Cashfree webhook event: "

                f"{event_type}"

            )

            webhook_event.processed_at = (

                datetime.now(timezone.utc)

            )

            self.payment_repository.save_webhook_event()

            raise HTTPException(

                status_code=400,

                detail=(

                    "Unsupported Cashfree webhook event: "

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
