import app.db.models

from app.db.session import SessionLocal
from app.modules.shop.order.models.order import Order
from app.modules.shop.order.models.order_status_history import (
    OrderStatusHistory,
)


db = SessionLocal()

try:
    orders = db.query(Order).order_by(Order.id).all()

    added = 0

    for order in orders:
        existing_initial = (
            db.query(OrderStatusHistory)
            .filter(
                OrderStatusHistory.order_id == order.id,
                OrderStatusHistory.status == "pending_payment",
            )
            .first()
        )

        if existing_initial is not None:
            continue

        history = OrderStatusHistory(
            order_id=order.id,
            status="pending_payment",
            note="Order created.",
            changed_by="system",
        )

        db.add(history)
        added += 1

        print(
            f"Added initial history: "
            f"{order.order_number} -> pending_payment"
        )

    db.commit()

    print()
    print(f"Backfill completed. Added {added} history records.")

except Exception:
    db.rollback()
    raise

finally:
    db.close()