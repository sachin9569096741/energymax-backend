
import logging
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.shiprocket import ShiprocketClient, ShiprocketError
from app.modules.shop.order.models.order import Order
from app.modules.shop.payment.models.payment import Payment
from app.modules.shop.payment.services.payment_state import PaymentStatus
from app.modules.shop.shipping.models.shipment import Shipment
from app.modules.shop.shipping.repositories.shipment import (
    ShipmentRepository,
)
from app.modules.shop.shipping.schemas.shipment import (
    ShipmentCreateRequest,
)

logger = logging.getLogger(__name__)

SHIPROCKET_PICKUP_LOCATION = "warehouse"


class ShipmentService:
    def __init__(self, db, shiprocket_client=None):
        self.db = db
        self.repository = ShipmentRepository(db)
        self.shiprocket = shiprocket_client or ShiprocketClient()

    def create_shipment(
        self,
        *,
        order_public_id: str,
        package: ShipmentCreateRequest,
    ) -> Shipment:
        """
        Create a Shiprocket shipment for a packed, successfully paid order.

        A persisted 'creating' record prevents a second local request.
        Any uncertain external result is retained for reconciliation;
        this method never automatically retries shipment creation.
        """

        # Lock the order while checking eligibility and reserving its
        # single local shipment record.
        order = self.db.scalar(
            select(Order)
            .where(Order.public_id == order_public_id)
            .with_for_update()
        )

        if order is None:
            raise ValueError("Order not found.")

        payment = self.db.scalar(
            select(Payment).where(Payment.order_id == order.id)
        )

        if payment is None or payment.status != PaymentStatus.SUCCEEDED:
            raise ValueError(
                "A successfully completed payment is required."
            )

        if order.status != "packed":
            raise ValueError(
                "Only packed orders can be submitted for shipping."
            )

        existing = self.repository.get_by_order_id(
            order.id,
            for_update=True,
        )

        if existing is not None:
            raise ValueError(
                f"A shipment record already exists with status "
                f"'{existing.status}'. Reconcile it before attempting "
                "another Shiprocket order."
            )

        self._validate_package(package)
        payload = self._build_shiprocket_payload(order, package)

        shipment = Shipment(
            order_id=order.id,
            status="creating",
            length_cm=package.length_cm,
            breadth_cm=package.breadth_cm,
            height_cm=package.height_cm,
            weight_kg=package.weight_kg,
        )

        try:
            self.repository.create(shipment)
            # Persist the unique local record BEFORE calling Shiprocket.
            self.db.commit()
            self.db.refresh(shipment)
        except IntegrityError:
            self.db.rollback()
            raise ValueError(
                "A shipment record already exists for this order."
            ) from None
        except Exception:
            self.db.rollback()
            raise

        try:
            response = self.shiprocket.request(
                "POST",
                "/orders/create/adhoc",
                json=payload,
            )
        except ShiprocketError:
            # The request may have reached Shiprocket even if our client
            # received an error or timed out. Do not retry automatically.
            shipment.status = "creation_unknown"
            shipment.last_error = (
                "Shiprocket creation outcome could not be confirmed. "
                "Reconcile the order in Shiprocket before retrying."
            )
            self.db.commit()
            self.db.refresh(shipment)

            logger.warning(
                "Shiprocket shipment outcome requires reconciliation "
                "for order %s",
                order.order_number,
            )
            raise ShiprocketError(
                "Shiprocket creation could not be confirmed. "
                "Check Shiprocket before attempting another shipment."
            ) from None
        except Exception:
            # Treat unexpected client failures conservatively too.
            shipment.status = "creation_unknown"
            shipment.last_error = (
                "Unexpected error during Shiprocket creation. "
                "Reconciliation is required before retrying."
            )
            self.db.commit()
            raise ShiprocketError(
                "Shipment creation outcome is uncertain. "
                "Reconcile it before retrying."
            ) from None

        if not isinstance(response, dict):
            shipment.status = "creation_unknown"
            shipment.last_error = (
                "Shiprocket returned an unexpected response. "
                "Reconciliation is required."
            )
            self.db.commit()
            raise ShiprocketError(
                "Shiprocket returned an unexpected response. "
                "Check Shiprocket before retrying."
            )

        data = response.get("data")
        if not isinstance(data, dict):
            data = response

        shiprocket_order_id = data.get("order_id")
        shiprocket_shipment_id = data.get("shipment_id")

        if not shiprocket_order_id or not shiprocket_shipment_id:
            shipment.status = "creation_unknown"
            shipment.last_error = (
                "Shiprocket response did not contain the expected "
                "order and shipment identifiers. Reconciliation is required."
            )
            self.db.commit()
            raise ShiprocketError(
                "Shiprocket response could not be confirmed. "
                "Check Shiprocket before retrying."
            )

        shipment.shiprocket_order_id = str(shiprocket_order_id)
        shipment.shiprocket_shipment_id = str(shiprocket_shipment_id)
        shipment.status = "created"
        shipment.last_error = None

        try:
            self.db.commit()
            self.db.refresh(shipment)
        except Exception:
            self.db.rollback()
            logger.exception(
                "Shiprocket accepted order %s, but saving the response "
                "failed. Reconciliation is required.",
                order.order_number,
            )
            raise ShiprocketError(
                "Shiprocket may have created the shipment, but its "
                "details could not be saved. Reconcile before retrying."
            ) from None

        return shipment

    @staticmethod
    def _validate_package(package: ShipmentCreateRequest) -> None:
        values = (
            package.length_cm,
            package.breadth_cm,
            package.height_cm,
            package.weight_kg,
        )

        if any(
            not value.is_finite() or value <= Decimal("0")
            for value in values
        ):
            raise ValueError(
                "Package dimensions and weight must be finite "
                "positive numbers."
            )

    @staticmethod
    def _build_shiprocket_payload(
        order: Order,
        package: ShipmentCreateRequest,
    ) -> dict:
        address = order.shipping_address_snapshot or {}

        recipient_name = (
            address.get("recipient_name") or order.customer_name or ""
        ).strip()

        name_parts = recipient_name.split(maxsplit=1)
        first_name = name_parts[0] if name_parts else ""
        last_name = name_parts[1] if len(name_parts) > 1 else ""

        phone = address.get("phone") or order.customer_phone
        email = order.customer_email

        address_line1 = address.get("address_line1")
        city = address.get("city")
        state = address.get("state")
        pincode = address.get("postal_code")
        country = address.get("country")

        if not all(
            [
                first_name,
                phone,
                email,
                address_line1,
                city,
                state,
                pincode,
                country,
            ]
        ):
            raise ValueError(
                "The order is missing required shipping address or "
                "customer contact details."
            )

        if not order.items:
            raise ValueError("Cannot ship an order without items.")

        order_items = []

        for item in order.items:
            order_items.append(
                {
                    "name": item.product_name,
                    # Use the immutable order-item ID as a fallback
                    # reference until a canonical product SKU is available.
                    "sku": item.public_id,
                    "units": item.quantity,
                    "selling_price": float(item.unit_price),
                }
            )

        address_line2 = " ".join(
            str(value).strip()
            for value in (
                address.get("address_line2"),
                address.get("landmark"),
            )
            if value and str(value).strip()
        )

        return {
            "order_id": order.order_number,
            "order_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "pickup_location": SHIPROCKET_PICKUP_LOCATION,
            "channel_id": "",
            "comment": f"EnergyMax order {order.order_number}",
            "billing_customer_name": first_name,
            "billing_last_name": last_name,
            "billing_address": address_line1,
            "billing_address_2": address_line2,
            "billing_city": city,
            "billing_pincode": str(pincode),
            "billing_state": state,
            "billing_country": country,
            "billing_email": email,
            "billing_phone": str(phone),
            "shipping_is_billing": True,
            "order_items": order_items,
            "payment_method": "Prepaid",
            "sub_total": float(order.subtotal),
            "length": float(package.length_cm),
            "breadth": float(package.breadth_cm),
            "height": float(package.height_cm),
            "weight": float(package.weight_kg),
        }
