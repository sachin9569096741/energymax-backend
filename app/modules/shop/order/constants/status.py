from typing import Final


# All supported order statuses
PENDING_PAYMENT: Final[str] = "pending_payment"
PAID: Final[str] = "paid"
CONFIRMED: Final[str] = "confirmed"
PROCESSING: Final[str] = "processing"
PACKED: Final[str] = "packed"
SHIPPED: Final[str] = "shipped"
OUT_FOR_DELIVERY: Final[str] = "out_for_delivery"
DELIVERED: Final[str] = "delivered"

CANCELLED: Final[str] = "cancelled"
REFUND_PENDING: Final[str] = "refund_pending"
REFUNDED: Final[str] = "refunded"

RETURN_REQUESTED: Final[str] = "return_requested"
RETURNED: Final[str] = "returned"


ORDER_STATUSES: Final[set[str]] = {
    PENDING_PAYMENT,
    PAID,
    CONFIRMED,
    PROCESSING,
    PACKED,
    SHIPPED,
    OUT_FOR_DELIVERY,
    DELIVERED,
    CANCELLED,
    REFUND_PENDING,
    REFUNDED,
    RETURN_REQUESTED,
    RETURNED,
}


# Allowed status transitions.
#
# Key   = current status
# Value = statuses that can come next
ORDER_STATUS_TRANSITIONS: Final[dict[str, set[str]]] = {
    PENDING_PAYMENT: {
        PAID,
        CANCELLED,
    },

    PAID: {
        CONFIRMED,
        CANCELLED,
        REFUND_PENDING,
    },

    CONFIRMED: {
        PROCESSING,
        CANCELLED,
    },

    PROCESSING: {
        PACKED,
        CANCELLED,
    },

    PACKED: {
        SHIPPED,
    },

    SHIPPED: {
        OUT_FOR_DELIVERY,
    },

    OUT_FOR_DELIVERY: {
        DELIVERED,
    },

    DELIVERED: {
        RETURN_REQUESTED,
    },

    REFUND_PENDING: {
        REFUNDED,
    },

    RETURN_REQUESTED: {
        RETURNED,
    },

    # Terminal states
    CANCELLED: set(),
    REFUNDED: set(),
    RETURNED: set(),
}



ORDER_STATUS_LABELS: Final[dict[str, str]] = {
    PENDING_PAYMENT: "Order Placed",
    PAID: "Payment Confirmed",
    CONFIRMED: "Order Confirmed",
    PROCESSING: "Processing",
    PACKED: "Packed",
    SHIPPED: "Shipped",
    OUT_FOR_DELIVERY: "Out for Delivery",
    DELIVERED: "Delivered",
    CANCELLED: "Cancelled",
    REFUND_PENDING: "Refund Pending",
    REFUNDED: "Refunded",
    RETURN_REQUESTED: "Return Requested",
    RETURNED: "Returned",
}