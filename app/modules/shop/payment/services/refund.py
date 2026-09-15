from decimal import Decimal
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.modules.shop.payment.models.payment_event import PaymentEvent
from app.modules.shop.payment.models.payment_refund import PaymentRefund
from app.modules.shop.payment.providers.exceptions import (
    PaymentProviderError,
)
from app.modules.shop.payment.router.payment_router import PaymentRouter
from app.modules.shop.payment.repositories.payment import PaymentRepository
from app.modules.shop.payment.repositories.refund import RefundRepository
from app.modules.shop.payment.services.payment_state import (
    PaymentStatus,
    transition_payment_status,
)


class RefundService:
    """
    Handles payment refunds.

    Responsibilities:
    - Validate refund requests
    - Enforce idempotency
    - Prevent over-refunding
    - Call payment provider
    - Persist refund state
    - Update payment state
    - Create payment audit events
    """

    def __init__(self, db: Session):
        self.db = db
        self.payment_repository = PaymentRepository(db)
        self.refund_repository = RefundRepository(db)
        self.payment_router = PaymentRouter()

    def create_refund(
        self,
        *,
        payment_public_id: str,
        customer,
        amount: Decimal | None,
        idempotency_key: str,
        reason: str | None = None,
    ) -> PaymentRefund:

        # ---------------------------------------------------------
        # 1. Validate idempotency key
        # ---------------------------------------------------------

        if not idempotency_key:
            raise HTTPException(
                status_code=400,
                detail="Idempotency-Key is required.",
            )

        idempotency_key = idempotency_key.strip()

        if not idempotency_key:
            raise HTTPException(
                status_code=400,
                detail="Idempotency-Key cannot be empty.",
            )

        if len(idempotency_key) > 128:
            raise HTTPException(
                status_code=400,
                detail="Idempotency-Key is too long.",
            )

        # ---------------------------------------------------------
        # 2. Get payment
        # ---------------------------------------------------------

        payment = self.payment_repository.get_by_public_id(
            public_id=payment_public_id,
            customer_id=customer.id,
        )

        if payment is None:
            raise HTTPException(
                status_code=404,
                detail="Payment not found.",
            )

        # ---------------------------------------------------------
        # 3. Idempotency check
        # ---------------------------------------------------------

        existing_refund = (
            self.refund_repository.get_by_idempotency_key(
                payment_id=payment.id,
                idempotency_key=idempotency_key,
            )
        )

        if existing_refund is not None:
            return existing_refund

        # ---------------------------------------------------------
        # 4. Payment must be refundable
        # ---------------------------------------------------------

        if payment.status not in {
            PaymentStatus.SUCCEEDED,
            PaymentStatus.PARTIALLY_REFUNDED,
        }:
            raise HTTPException(
                status_code=400,
                detail="Only successful payments can be refunded.",
            )

        # ---------------------------------------------------------
        # 5. Validate payment amount
        # ---------------------------------------------------------

        payment_amount = Decimal(str(payment.amount))

        if payment_amount <= Decimal("0"):
            raise HTTPException(
                status_code=400,
                detail="Payment amount must be greater than zero.",
            )

        # ---------------------------------------------------------
        # 6. Resolve refund amount
        # ---------------------------------------------------------

        if amount is None:
            refund_amount = payment_amount
        else:
            refund_amount = Decimal(str(amount))

        if refund_amount <= Decimal("0"):
            raise HTTPException(
                status_code=400,
                detail="Refund amount must be greater than zero.",
            )

        if refund_amount > payment_amount:
            raise HTTPException(
                status_code=400,
                detail="Refund amount cannot exceed payment amount.",
            )

        # ---------------------------------------------------------
        # 7. Calculate already refunded amount
        # ---------------------------------------------------------

        already_refunded = (
            self.refund_repository.get_total_refunded(
                payment_id=payment.id,
            )
        )

        remaining_amount = (
            payment_amount - already_refunded
        )

        if remaining_amount <= Decimal("0"):
            raise HTTPException(
                status_code=400,
                detail="Payment has already been fully refunded.",
            )

        if refund_amount > remaining_amount:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Refund amount exceeds remaining refundable "
                    f"amount of {remaining_amount}."
                ),
            )

        # ---------------------------------------------------------
        # 8. Resolve provider
        # ---------------------------------------------------------

        provider_name = payment.provider

        if not provider_name:
            raise HTTPException(
                status_code=400,
                detail="Payment provider is missing.",
            )

        provider = self.payment_router.get_provider(
            provider_name
        )

        # ---------------------------------------------------------
        # 9. Provider payment ID required
        # ---------------------------------------------------------

        if not payment.provider_payment_id:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Provider payment ID is missing. "
                    "Refund cannot be processed."
                ),
            )

        # ---------------------------------------------------------
        # 10. Create local refund record
        # ---------------------------------------------------------

        refund = PaymentRefund(
            public_id=str(uuid4()),
            payment_id=payment.id,
            amount=refund_amount,
            currency=payment.currency,
            status="pending",
            provider=provider_name,
            idempotency_key=idempotency_key,
            reason=reason,
        )

        self.refund_repository.create(refund)

        # ---------------------------------------------------------
        # 11. Create audit event
        # ---------------------------------------------------------

        self.payment_repository.create_event(
            PaymentEvent(
                public_id=str(uuid4()),
                payment_id=payment.id,
                attempt_id=None,
                event_type="refund_created",
                status="pending",
                message="Refund request created.",
                event_data={
                    "refund_id": refund.public_id,
                    "amount": str(refund_amount),
                    "currency": refund.currency,
                    "provider": provider_name,
                    "reason": reason,
                },
            )
        )

        # ---------------------------------------------------------
        # 12. Call provider
        # ---------------------------------------------------------

        try:
            provider_response = provider.refund_payment(
                provider_payment_id=payment.provider_payment_id,
                amount=refund_amount,
                currency=payment.currency,
                metadata={
                    "refund_id": refund.public_id,
                    "reason": reason,
                },
            )

        except PaymentProviderError as exc:

            refund.status = "failed"
            refund.failure_code = exc.code
            refund.failure_message = exc.message

            self.payment_repository.create_event(
                PaymentEvent(
                    public_id=str(uuid4()),
                    payment_id=payment.id,
                    attempt_id=None,
                    event_type="refund_failed",
                    status="failed",
                    message=exc.message,
                    event_data={
                        "refund_id": refund.public_id,
                        "amount": str(refund_amount),
                        "currency": refund.currency,
                        "provider": provider_name,
                        "code": exc.code,
                    },
                )
            )

            self.refund_repository.save()

            raise HTTPException(
                status_code=502,
                detail="Payment provider refund failed.",
            ) from exc

        except Exception as exc:

            refund.status = "failed"
            refund.failure_code = "REFUND_FAILED"
            refund.failure_message = str(exc)

            self.payment_repository.create_event(
                PaymentEvent(
                    public_id=str(uuid4()),
                    payment_id=payment.id,
                    attempt_id=None,
                    event_type="refund_failed",
                    status="failed",
                    message="Unexpected refund provider error.",
                    event_data={
                        "refund_id": refund.public_id,
                        "amount": str(refund_amount),
                        "currency": refund.currency,
                        "provider": provider_name,
                    },
                )
            )

            self.refund_repository.save()

            raise HTTPException(
                status_code=502,
                detail="Payment provider refund failed.",
            ) from exc

        # ---------------------------------------------------------
        # 13. Validate provider response
        # ---------------------------------------------------------

        if not isinstance(provider_response, dict):
            refund.status = "failed"
            refund.failure_code = "INVALID_PROVIDER_RESPONSE"
            refund.failure_message = (
                "Payment provider returned an invalid refund response."
            )

            self.refund_repository.save()

            raise HTTPException(
                status_code=502,
                detail="Invalid payment provider refund response.",
            )

        # ---------------------------------------------------------
        # 14. Get provider refund ID
        # ---------------------------------------------------------

        provider_refund_id = provider_response.get(
            "provider_refund_id"
        )

        if not provider_refund_id:
            refund.status = "failed"
            refund.failure_code = "MISSING_REFUND_ID"
            refund.failure_message = (
                "Payment provider did not return a refund ID."
            )

            self.payment_repository.create_event(
                PaymentEvent(
                    public_id=str(uuid4()),
                    payment_id=payment.id,
                    attempt_id=None,
                    event_type="refund_failed",
                    status="failed",
                    message="Provider refund ID missing.",
                    event_data={
                        "refund_id": refund.public_id,
                        "provider": provider_name,
                    },
                )
            )

            self.refund_repository.save()

            raise HTTPException(
                status_code=502,
                detail="Invalid payment provider refund response.",
            )

        # ---------------------------------------------------------
        # 15. Validate provider amount
        # ---------------------------------------------------------

        provider_amount = provider_response.get("amount")

        if provider_amount is not None:

            provider_amount = Decimal(
                str(provider_amount)
            )

            if provider_amount != refund_amount:

                refund.status = "failed"
                refund.failure_code = "AMOUNT_MISMATCH"
                refund.failure_message = (
                    "Provider refund amount does not match "
                    "requested refund amount."
                )

                self.payment_repository.create_event(
                    PaymentEvent(
                        public_id=str(uuid4()),
                        payment_id=payment.id,
                        attempt_id=None,
                        event_type="refund_failed",
                        status="failed",
                        message="Provider refund amount mismatch.",
                        event_data={
                            "refund_id": refund.public_id,
                            "requested_amount": str(refund_amount),
                            "provider_amount": str(provider_amount),
                        },
                    )
                )

                self.refund_repository.save()

                raise HTTPException(
                    status_code=502,
                    detail=(
                        "Payment provider refund amount mismatch."
                    ),
                )

        # ---------------------------------------------------------
        # 16. Validate provider currency
        # ---------------------------------------------------------

        provider_currency = provider_response.get(
            "currency"
        )

        if provider_currency and (
            provider_currency.upper()
            != payment.currency.upper()
        ):
            refund.status = "failed"
            refund.failure_code = "CURRENCY_MISMATCH"
            refund.failure_message = (
                "Provider refund currency does not match "
                "payment currency."
            )

            self.payment_repository.create_event(
                PaymentEvent(
                    public_id=str(uuid4()),
                    payment_id=payment.id,
                    attempt_id=None,
                    event_type="refund_failed",
                    status="failed",
                    message="Provider refund currency mismatch.",
                    event_data={
                        "refund_id": refund.public_id,
                        "payment_currency": payment.currency,
                        "provider_currency": provider_currency,
                    },
                )
            )

            self.refund_repository.save()

            raise HTTPException(
                status_code=502,
                detail=(
                    "Payment provider refund currency mismatch."
                ),
            )

        # ---------------------------------------------------------
        # 17. Save provider refund data
        # ---------------------------------------------------------

        refund.provider_refund_id = provider_refund_id

        refund.provider_response = provider_response.get(
            "raw_response"
        )

        # ---------------------------------------------------------
        # 18. Determine refund status
        # ---------------------------------------------------------

        provider_status = (
            provider_response.get("status") or ""
        ).lower()

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

        else:
            refund.status = "pending"

        # ---------------------------------------------------------
        # 19. Update payment status
        # ---------------------------------------------------------

        if refund.status == "succeeded":

            total_refunded = (
                already_refunded + refund_amount
            )

            if total_refunded >= payment_amount:

                transition_payment_status(
                    payment,
                    PaymentStatus.REFUNDED,
                )

            else:

                transition_payment_status(
                    payment,
                    PaymentStatus.PARTIALLY_REFUNDED,
                )

        # ---------------------------------------------------------
        # 20. Create final audit event
        # ---------------------------------------------------------

        if refund.status == "succeeded":

            event_type = "refund_succeeded"
            event_status = "succeeded"
            event_message = "Refund processed successfully."

        elif refund.status == "failed":

            event_type = "refund_failed"
            event_status = "failed"
            event_message = "Payment provider reported refund failure."

            refund.failure_code = "PROVIDER_REFUND_FAILED"
            refund.failure_message = (
                "Payment provider reported refund failure."
            )

        else:

            event_type = "refund_pending"
            event_status = "pending"
            event_message = "Refund is pending with payment provider."

        self.payment_repository.create_event(
            PaymentEvent(
                public_id=str(uuid4()),
                payment_id=payment.id,
                attempt_id=None,
                event_type=event_type,
                status=event_status,
                message=event_message,
                event_data={
                    "refund_id": refund.public_id,
                    "provider_refund_id": (
                        refund.provider_refund_id
                    ),
                    "amount": str(refund_amount),
                    "currency": refund.currency,
                    "provider": provider_name,
                },
            )
        )

        # ---------------------------------------------------------
        # 21. Save
        # ---------------------------------------------------------

        self.refund_repository.save()

        return refund