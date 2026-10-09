from enum import Enum


class InventoryMovementType(str, Enum):
    PURCHASE = "PURCHASE"
    SALE = "SALE"
    RETURN = "RETURN"
    STOCK_IN = "STOCK_IN"
    STOCK_OUT = "STOCK_OUT"
    ADJUSTMENT = "ADJUSTMENT"
    DAMAGE = "DAMAGE"
    EXPIRED = "EXPIRED"
    CANCELLED_ORDER = "CANCELLED_ORDER"
    RESERVATION = "RESERVATION"
    RELEASE = "RELEASE"


class InventoryReservationStatus(str, Enum):
    ACTIVE = "ACTIVE"
    CONFIRMED = "CONFIRMED"
    RELEASED = "RELEASED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class StockAdjustmentType(str, Enum):
    INCREASE = "INCREASE"
    DECREASE = "DECREASE"