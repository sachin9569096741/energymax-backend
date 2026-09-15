from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.shop.customer.security.dependencies import (
    get_current_customer,
)

from app.modules.shop.payment.models.webhook_event import WebhookEvent
from app.modules.shop.payment.providers.exceptions import (
    PaymentProviderError,
    PaymentProviderSignatureError,
)
from app.modules.shop.payment.repositories.payment import PaymentRepository
from app.modules.shop.payment.router.payment_router import PaymentRouter
from app.modules.shop.payment.schemas.payment import (
    PaymentResponse,
    VerifyPaymentRequest,
)
from app.modules.shop.payment.services.payment import PaymentService


router = APIRouter(
    prefix="/payments",
    tags=["Shop - Payments"],
)


# =========================================================
# CREATE PAYMENT FROM ORDER
# =========================================================

@router.post(
    "/from-order/{order_public_id}",
    response_model=PaymentResponse,
    status_code=201,
)
def create_payment_from_order(
    order_public_id: str,
    current_customer=Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    service = PaymentService(db)

    try:
        payment = service.create_payment(
            order_public_id=order_public_id,
            customer=current_customer,
        )

        db.commit()
        db.refresh(payment)

        return payment

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to create payment.",
        )


# =========================================================
# VERIFY PAYMENT
# =========================================================

@router.post(
    "/{payment_public_id}/verify",
    response_model=PaymentResponse,
)
def verify_payment(
    payment_public_id: str,
    request: VerifyPaymentRequest,
    current_customer=Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    service = PaymentService(db)

    try:
        payment = service.verify_payment(
            payment_public_id=payment_public_id,
            request=request,
            customer=current_customer,
        )

        db.commit()
        db.refresh(payment)

        return payment

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Payment verification failed.",
        )


# =========================================================
# RAZORPAY WEBHOOK
# =========================================================

@router.post(
    "/webhooks/razorpay",
    status_code=200,
)
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str | None = Header(
        default=None,
        alias="X-Razorpay-Signature",
    ),
    db: Session = Depends(get_db),
):
    # ---------------------------------------------------------
    # 1. Validate signature header
    # ---------------------------------------------------------

    if not x_razorpay_signature:
        raise HTTPException(
            status_code=400,
            detail="Missing Razorpay webhook signature.",
        )

    # ---------------------------------------------------------
    # 2. Read exact raw request body
    # ---------------------------------------------------------

    raw_body = await request.body()

    if not raw_body:
        raise HTTPException(
            status_code=400,
            detail="Empty webhook payload.",
        )

    # ---------------------------------------------------------
    # 3. Resolve Razorpay provider
    # ---------------------------------------------------------

    payment_router = PaymentRouter()

    provider = payment_router.get_provider(
        "razorpay"
    )

    # ---------------------------------------------------------
    # 4. Verify signature BEFORE parsing JSON
    #
    # IMPORTANT:
    # Razorpay signs the exact raw request body.
    # Never reconstruct JSON before signature verification.
    # ---------------------------------------------------------

    try:
        provider.verify_webhook(
            payload=raw_body,
            signature=x_razorpay_signature,
        )

    except PaymentProviderSignatureError as exc:
        db.rollback()

        raise HTTPException(
            status_code=400,
            detail="Invalid Razorpay webhook signature.",
        ) from exc

    # ---------------------------------------------------------
    # 5. Parse JSON
    # ---------------------------------------------------------

    try:
        payload = await request.json()

    except Exception as exc:
        db.rollback()

        raise HTTPException(
            status_code=400,
            detail="Invalid webhook JSON payload.",
        ) from exc

    # ---------------------------------------------------------
    # 6. Validate webhook structure
    # ---------------------------------------------------------

    event_id = payload.get("id")

    event_type = payload.get("event")

    if not event_id:
        raise HTTPException(
            status_code=400,
            detail="Webhook event ID is missing.",
        )

    if not event_type:
        raise HTTPException(
            status_code=400,
            detail="Webhook event type is missing.",
        )

    # ---------------------------------------------------------
    # 7. Parse / normalize Razorpay payload
    #
    # Do this before storing the webhook so malformed/
    # unsupported events are rejected cleanly.
    # ---------------------------------------------------------

    try:
        normalized = provider.parse_webhook(
            payload=payload,
        )

    except PaymentProviderError as exc:
        db.rollback()

        raise HTTPException(
            status_code=400,
            detail=exc.message,
        ) from exc

    # ---------------------------------------------------------
    # 8. Atomically create webhook event
    #
    # Uses:
    #
    # UNIQUE(provider, event_id)
    #
    # + PostgreSQL ON CONFLICT DO NOTHING
    #
    # This protects against concurrent duplicate webhook
    # requests.
    # ---------------------------------------------------------

    payment_repository = PaymentRepository(db)

    new_webhook_event = WebhookEvent(
        public_id=str(uuid4()),
        provider="razorpay",
        event_id=event_id,
        event_type=event_type,
        status="received",
        payload=payload,
        signature=x_razorpay_signature,
    )

    webhook_event = (
        payment_repository.create_webhook_event_if_new(
            new_webhook_event
        )
    )

    # ---------------------------------------------------------
    # 9. Duplicate webhook
    # ---------------------------------------------------------

    if webhook_event is None:

        existing_event = (
            payment_repository.get_webhook_event(
                provider="razorpay",
                event_id=event_id,
            )
        )

        if existing_event is None:
            db.rollback()

            raise HTTPException(
                status_code=500,
                detail=(
                    "Webhook idempotency check failed."
                ),
            )

        # -----------------------------------------------------
        # Already completed / intentionally ignored
        # -----------------------------------------------------

        if existing_event.status in {
            "processed",
            "ignored",
        }:
            return {
                "status": "already_processed",
                "event_id": event_id,
            }

        # -----------------------------------------------------
        # Existing received/failed event
        #
        # This allows a retry if an earlier processing attempt
        # was persisted in a retryable state.
        # -----------------------------------------------------

        webhook_event = existing_event

        try:
            normalized = provider.parse_webhook(
                payload=webhook_event.payload,
            )

        except PaymentProviderError as exc:
            webhook_event.status = "failed"
            webhook_event.error_message = exc.message

            payment_repository.save_webhook_event()
            db.commit()

            raise HTTPException(
                status_code=400,
                detail=exc.message,
            ) from exc

    # ---------------------------------------------------------
    # 10. Process payment
    # ---------------------------------------------------------

    service = PaymentService(db)

    try:
        service.process_razorpay_webhook(
            webhook_event=webhook_event,
            normalized=normalized,
        )

        db.commit()

    except HTTPException:
        db.rollback()
        raise

    except Exception as exc:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Webhook processing failed.",
        ) from exc

    # ---------------------------------------------------------
    # 11. Success
    # ---------------------------------------------------------

    return {
        "status": "processed",
        "event_id": event_id,
    }