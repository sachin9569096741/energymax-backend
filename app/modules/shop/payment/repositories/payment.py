from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.modules.shop.payment.models.payment import Payment
from app.modules.shop.payment.models.payment_attempt import PaymentAttempt
from app.modules.shop.payment.models.payment_event import PaymentEvent
from app.modules.shop.payment.models.webhook_event import WebhookEvent


class PaymentRepository:

    def __init__(self, db: Session):
        self.db = db

    # =========================================================
    # PAYMENT
    # =========================================================

    def get_by_public_id(
        self,
        public_id: str,
        customer_id: int,
    ) -> Payment | None:
        statement = (
            select(Payment)
            .where(
                Payment.public_id == public_id,
                Payment.customer_id == customer_id,
            )
        )

        return self.db.scalar(statement)

    def get_by_order_id(
        self,
        order_id: int,
    ) -> Payment | None:
        statement = (
            select(Payment)
            .where(
                Payment.order_id == order_id,
            )
        )

        return self.db.scalar(statement)

    def get_by_provider_order_id(
        self,
        provider_order_id: str,
    ) -> Payment | None:
        statement = (
            select(Payment)
            .where(
                Payment.provider_order_id
                == provider_order_id
            )
        )

        return self.db.scalar(statement)

    def create(
        self,
        payment: Payment,
    ) -> Payment:
        self.db.add(payment)
        self.db.flush()

        return payment

    # =========================================================
    # PAYMENT ATTEMPT
    # =========================================================

    def get_next_attempt_number(
        self,
        payment_id: int,
    ) -> int:
        statement = (
            select(PaymentAttempt.attempt_number)
            .where(
                PaymentAttempt.payment_id == payment_id,
            )
            .order_by(
                PaymentAttempt.attempt_number.desc()
            )
            .limit(1)
        )

        latest_number = self.db.scalar(statement)

        if latest_number is None:
            return 1

        return latest_number + 1

    def create_attempt(
        self,
        attempt: PaymentAttempt,
    ) -> PaymentAttempt:
        self.db.add(attempt)
        self.db.flush()

        return attempt

    def get_latest_attempt(
        self,
        payment_id: int,
    ) -> PaymentAttempt | None:
        statement = (
            select(PaymentAttempt)
            .where(
                PaymentAttempt.payment_id == payment_id,
            )
            .order_by(
                PaymentAttempt.attempt_number.desc()
            )
            .limit(1)
        )

        return self.db.scalar(statement)


    
    def get_attempt_by_provider_order_id(
        self,
        payment_id: int,
        provider_order_id: str,
    ) -> PaymentAttempt | None:
        statement = (
            select(PaymentAttempt)
            .where(
                PaymentAttempt.payment_id == payment_id,
                PaymentAttempt.provider_order_id == provider_order_id,
            )
            .limit(1)
        )

        return self.db.scalar(statement)

    # =========================================================
    # PAYMENT EVENT
    # =========================================================

    def create_event(
        self,
        event: PaymentEvent,
    ) -> PaymentEvent:
        self.db.add(event)
        self.db.flush()

        return event

    # =========================================================
    # WEBHOOK EVENT
    # =========================================================

    def get_webhook_event(
        self,
        *,
        provider: str,
        event_id: str,
    ) -> WebhookEvent | None:
        statement = (
            select(WebhookEvent)
            .where(
                WebhookEvent.provider == provider,
                WebhookEvent.event_id == event_id,
            )
        )

        return self.db.scalar(statement)

    def create_webhook_event(
        self,
        webhook_event: WebhookEvent,
    ) -> WebhookEvent:
        """
        Normal webhook event creation.

        Use create_webhook_event_if_new() for webhook
        endpoints where concurrent duplicate requests
        must be handled safely.
        """

        self.db.add(webhook_event)
        self.db.flush()

        return webhook_event

    def create_webhook_event_if_new(
        self,
        webhook_event: WebhookEvent,
    ) -> WebhookEvent | None:
        """
        Atomically create a webhook event.

        Returns:
            WebhookEvent:
                When this event was newly inserted.

            None:
                When the same provider/event_id already exists.

        This relies on the database constraint:

            UNIQUE(provider, event_id)

        and PostgreSQL:

            ON CONFLICT DO NOTHING

        This prevents two concurrent webhook requests from
        processing the same Razorpay event twice.
        """

        statement = (
            insert(WebhookEvent)
            .values(
                provider=webhook_event.provider,
                event_id=webhook_event.event_id,
                event_type=webhook_event.event_type,
                status=webhook_event.status,
                payload=webhook_event.payload,
                signature=webhook_event.signature,
            )
            .on_conflict_do_nothing(
                index_elements=[
                    WebhookEvent.provider,
                    WebhookEvent.event_id,
                ]
            )
            .returning(WebhookEvent.id)
        )

        inserted_id = self.db.scalar(statement)

        # Another request already inserted the same
        # provider/event_id.
        if inserted_id is None:
            return None

        # Load the actual ORM object that was inserted.
        # This is important because the caller will later
        # modify status / processed_at / error_message.
        created_event = self.db.get(
            WebhookEvent,
            inserted_id,
        )

        return created_event

    def save_webhook_event(self) -> None:
        self.db.flush()

    # =========================================================
    # GENERAL SAVE
    # =========================================================

    def save(self) -> None:
        self.db.flush()