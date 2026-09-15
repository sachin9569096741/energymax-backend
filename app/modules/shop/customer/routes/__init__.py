from app.modules.shop.customer.routes.auth import router as customer_auth_router
from app.modules.shop.customer.routes.address import router as customer_address_router
from app.modules.shop.customer.routes.otp import (
    router as customer_otp_router,
)

__all__ = [
    "customer_auth_router",
    "customer_address_router",
    "customer_otp_router",
]