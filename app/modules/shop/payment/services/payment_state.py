from fastapi import HTTPException


class PaymentStatus:
    CREATED = "created"
    PENDING = "pending"
    AUTHORIZED = "authorized"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUND_PENDING = "refund_pending"
    PARTIALLY_REFUNDED = "partially_refunded"
    REFUNDED = "refunded"


ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    PaymentStatus.CREATED: {
        PaymentStatus.PENDING,
        PaymentStatus.CANCELLED,
    },
    PaymentStatus.PENDING: {
        PaymentStatus.AUTHORIZED,
        PaymentStatus.SUCCEEDED,
        PaymentStatus.FAILED,
        PaymentStatus.CANCELLED,
    },
    PaymentStatus.AUTHORIZED: {
        PaymentStatus.SUCCEEDED,
        PaymentStatus.FAILED,
        PaymentStatus.CANCELLED,
    },
    PaymentStatus.SUCCEEDED: {
        PaymentStatus.REFUND_PENDING,
        PaymentStatus.PARTIALLY_REFUNDED,
        PaymentStatus.REFUNDED,
    },
    PaymentStatus.FAILED: {
        PaymentStatus.PENDING,
        PaymentStatus.CANCELLED,
    },
    PaymentStatus.CANCELLED: set(),
    PaymentStatus.REFUND_PENDING: {
        PaymentStatus.PARTIALLY_REFUNDED,
        PaymentStatus.REFUNDED,
    },
    PaymentStatus.PARTIALLY_REFUNDED: {
        PaymentStatus.REFUND_PENDING,
        PaymentStatus.REFUNDED,
    },
    PaymentStatus.REFUNDED: set(),
}


def transition_payment_status(payment, new_status: str) -> None:
    current_status = payment.status

    if current_status == new_status:
        return

    allowed_statuses = ALLOWED_TRANSITIONS.get(current_status, set())

    if new_status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid payment status transition: "
                f"{current_status} -> {new_status}."
            ),
        )

    payment.status = new_status