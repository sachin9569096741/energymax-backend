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

    except PaymentProviderError as exc:
        db.rollback()

        raise HTTPException(
            status_code=502,
            detail={
                "message": exc.message,
                "provider": exc.provider,
                "code": exc.code,
            },
        ) from exc

    except Exception as exc:
        db.rollback()

        print(
            "PAYMENT CREATE ERROR:",
            type(exc).__name__,
            str(exc),
        )

        raise HTTPException(
            status_code=500,
            detail="Failed to create payment.",
        ) from exc


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

    except PaymentProviderError as exc:
        db.rollback()

        raise HTTPException(
            status_code=502,
            detail={
                "message": exc.message,
                "provider": exc.provider,
                "code": exc.code,
            },
        ) from exc

    except Exception as exc:
        db.rollback()

        print(
            "PAYMENT VERIFY ERROR:",
            type(exc).__name__,
            str(exc),
        )

        raise HTTPException(
            status_code=500,
            detail="Payment verification failed.",
        ) from exc


# =========================================================
# CASHFREE WEBHOOK
# =========================================================

@router.post(
    "/webhooks/cashfree",
    status_code=200,
)
async def cashfree_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    # ---------------------------------------------------------
    # 1. Read exact raw request body
    # ---------------------------------------------------------

    raw_body = await request.body()

    if not raw_body:
        raise HTTPException(
            status_code=400,
            detail="Empty webhook payload.",
        )

    # ---------------------------------------------------------
    # 2. Resolve Cashfree provider
    # ---------------------------------------------------------

    payment_router = PaymentRouter()

    try:
        provider = payment_router.get_provider(
            "cashfree"
        )

    except HTTPException:
        db.rollback()
        raise

    # ---------------------------------------------------------
    # 3. Collect Cashfree webhook headers
    #
    # Cashfree signature verification requires:
    # - x-webhook-signature
    # - x-webhook-timestamp
    #
    # We pass the headers directly to the provider so the
    # provider layer remains responsible for verification.
    # ---------------------------------------------------------

    webhook_headers = {
        key.lower(): value
        for key, value in request.headers.items()
        if key.lower() in {
            "x-webhook-signature",
            "x-webhook-timestamp",
        }
    }

    # ---------------------------------------------------------
    # 4. Verify signature BEFORE parsing JSON
    #
    # IMPORTANT:
    # Cashfree signs:
    #
    # timestamp + raw request body
    #
    # Therefore we must use the exact raw bytes.
    # ---------------------------------------------------------

    try:
        provider.verify_webhook(
            payload=raw_body,
            headers=webhook_headers,
        )

    except PaymentProviderSignatureError as exc:
        db.rollback()

        raise HTTPException(
            status_code=400,
            detail="Invalid Cashfree webhook signature.",
        ) from exc

    except PaymentProviderError as exc:
        db.rollback()

        raise HTTPException(
            status_code=400,
            detail=exc.message,
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

    if not isinstance(payload, dict):
        db.rollback()

        raise HTTPException(
            status_code=400,
            detail="Invalid webhook payload.",
        )

    # ---------------------------------------------------------
    # 6. Parse / normalize Cashfree payload
    #
    # Adapter -> Mapper -> provider-neutral structure
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

    except Exception as exc:
        db.rollback()

        raise HTTPException(
            status_code=400,
            detail="Invalid Cashfree webhook payload.",
        ) from exc

    # ---------------------------------------------------------
    # 7. Validate normalized event ID
    # ---------------------------------------------------------

    event_id = normalized.get(
        "event_id"
    )

    event_type = normalized.get(
        "event_type"
    )

    if not event_id:
        db.rollback()

        raise HTTPException(
            status_code=400,
            detail="Webhook event ID is missing.",
        )

    if not event_type:
        db.rollback()

        raise HTTPException(
            status_code=400,
            detail="Webhook event type is missing.",
        )

    # ---------------------------------------------------------
    # 8. Atomically create webhook event
    #
    # UNIQUE(provider, event_id)
    # + PostgreSQL ON CONFLICT DO NOTHING
    #
    # This protects against duplicate/concurrent webhooks.
    # ---------------------------------------------------------

    payment_repository = PaymentRepository(db)

    new_webhook_event = WebhookEvent(
        public_id=str(uuid4()),
        provider="cashfree",
        event_id=event_id,
        event_type=event_type,
        status="received",
        payload=payload,
        signature=webhook_headers.get(
            "x-webhook-signature"
        ),
    )

    webhook_event = (
        payment_repository.create_webhook_event_if_new(
            new_webhook_event
        )
    )

    # ---------------------------------------------------------
    # 9. Handle duplicate webhook
    # ---------------------------------------------------------

    if webhook_event is None:

        existing_event = (
            payment_repository.get_webhook_event(
                provider="cashfree",
                event_id=event_id,
            )
        )

        if existing_event is None:
            db.rollback()

            raise HTTPException(
                status_code=500,
                detail="Webhook idempotency check failed.",
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
        # Allow retry of processing.
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
    # 10. Process Cashfree webhook
    # ---------------------------------------------------------

    service = PaymentService(db)

    try:
        service.process_cashfree_webhook(
            webhook_event=webhook_event,
            normalized=normalized,
        )

        db.commit()

    except HTTPException:
        db.rollback()
        raise

    except Exception as exc:
        db.rollback()

        print(
            "CASHFREE WEBHOOK PROCESSING ERROR:",
            type(exc).__name__,
            str(exc),
        )

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