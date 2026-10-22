
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ============================================================
# CORE
# ============================================================

from app.core import cloudinary


# ============================================================
# ADMIN - AUTHENTICATION & USER MANAGEMENT
# ============================================================

from app.modules.admin.auth.routes.auth import (
    router as admin_auth_router,
)

from app.modules.admin.auth.routes.admin_user import (
    router as admin_user_router,
)

from app.modules.admin.auth.routes.permissions import (
    router as admin_permissions_router,
    roles_router as admin_roles_router,
    user_permissions_router as admin_user_permissions_router,
)
from app.modules.affiliate.routes.referral import (
    router as affiliate_referral_router,
)


# ============================================================
# ADMIN - CUSTOMERS, ORDERS, ANALYTICS & NOTIFICATIONS
# ============================================================

from app.modules.admin.customer.routes.customer import (
    router as admin_customer_router,
)

from app.modules.admin.order.routes import (
    order_router as admin_order_router,
)

from app.modules.admin.analytics.routes.overview import (
    router as admin_analytics_router,
)

from app.modules.admin.notifications.routes.notification import (
    router as admin_notifications_router,
)


# ============================================================
# ADMIN - INVENTORY
# ============================================================

from app.modules.shop.inventory.routes.warehouse import (
    router as inventory_warehouse_router,
)

from app.modules.shop.inventory.routes.inventory_stock import (
    router as inventory_stock_router,
)

from app.modules.shop.inventory.routes.inventory_balance import (
    router as inventory_balance_router,
)

from app.modules.shop.inventory.routes.inventory_reservation import (
    router as inventory_reservation_router,
)

from app.modules.shop.inventory.routes.inventory_movement import (
    router as inventory_movement_router,
)

from app.modules.shop.inventory.routes.stock_adjustment import (
    router as stock_adjustment_router,
)


# ============================================================
# ADMIN - COUPONS
# ============================================================

from app.modules.shop.coupons.routes import (
    admin_router as admin_coupon_router,
)


# ============================================================
# AFFILIATE - PUBLIC, APPLICATIONS & ADMIN
# ============================================================

from app.modules.affiliate.routes.public import (
    router as affiliate_public_router,
)

from app.modules.affiliate.routes.admin import (
    router as affiliate_admin_router,
    affiliates_router as affiliates_admin_router,
)

from app.modules.shop.shipping.routes.webhook import (
    router as shipping_webhook_router,
)


from app.modules.affiliate.routes.admin_activation import (
    router as affiliate_activation_admin_router,
)


# ============================================================
# AFFILIATE - AUTHENTICATION
# ============================================================

from app.modules.affiliate.routes.auth import (
    router as affiliate_auth_router,
)


# ============================================================
# SHOP - CATALOG
# ============================================================

from app.modules.shop.catalog.routes.category import (
    router as category_router,
)

from app.modules.shop.catalog.routes.subcategory import (
    router as subcategory_router,
)

from app.modules.shop.catalog.routes.product import (
    router as product_router,
)

from app.modules.shop.catalog.routes.product_image import (
    router as product_image_router,
)

from app.modules.shop.catalog.routes.variant import (
    router as variant_router,
)


# ============================================================
# SHOP - CART
# ============================================================

from app.modules.shop.cart.routes.guest_cart import (
    router as guest_cart_router,
)

from app.modules.shop.cart.routes.customer_cart import (
    router as customer_cart_router,
)


# ============================================================
# SHOP - CUSTOMER AUTHENTICATION & PROFILE
# ============================================================

from app.modules.shop.customer.routes.auth import (
    router as customer_auth_router,
)

from app.modules.shop.customer.routes.forgot_password import (
    router as customer_forgot_password_router,
)

from app.modules.shop.customer.routes.otp import (
    router as customer_otp_router,
)

from app.modules.shop.customer.routes.profile import (
    router as profile_router,
)

from app.modules.shop.customer.routes.address import (
    router as customer_address_router,
)

from app.modules.shop.customer.routes.wishlist import (
    router as customer_wishlist_router,
)

from app.modules.shop.customer.notifications.routes.notification import (
    router as customer_notifications_router,
)


# ============================================================
# SHOP - COUPONS
# ============================================================

from app.modules.shop.coupons.routes import (
    customer_router as customer_coupon_router,
)


# ============================================================
# SHOP - CHECKOUT, ORDERS & PAYMENTS
# ============================================================

from app.modules.shop.checkout.routes.checkout import (
    router as checkout_router,
)

from app.modules.shop.order.routes.order import (
    router as order_router,
)

from app.modules.shop.payment.routes.payment import (
    router as payment_router,
)

from app.modules.shop.payment.routes.refund import (
    router as refund_router,
)


# ============================================================
# APPLICATION
# ============================================================

app = FastAPI(
    title="EnergyMax API",
    version="1.0.0",
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "https://energymaxgroup.in",
        "https://www.energymaxgroup.in",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# REGISTER ROUTERS
# ============================================================

# ------------------------------------------------------------
# ADMIN - AUTHENTICATION & USER MANAGEMENT
# ------------------------------------------------------------

app.include_router(admin_auth_router, prefix="/api/v1")
app.include_router(admin_permissions_router, prefix="/api/v1")
app.include_router(admin_user_router, prefix="/api/v1")
app.include_router(admin_roles_router, prefix="/api/v1")
app.include_router(admin_user_permissions_router, prefix="/api/v1")


# ------------------------------------------------------------
# ADMIN - CUSTOMERS, ORDERS, ANALYTICS & NOTIFICATIONS
# ------------------------------------------------------------

app.include_router(admin_customer_router, prefix="/api/v1")
app.include_router(admin_order_router, prefix="/api/v1")
app.include_router(admin_analytics_router, prefix="/api/v1")
app.include_router(admin_notifications_router, prefix="/api/v1")


# ------------------------------------------------------------
# ADMIN - INVENTORY
# ------------------------------------------------------------

app.include_router(
    inventory_warehouse_router,
    prefix="/api/v1/admin/inventory",
)

app.include_router(
    inventory_stock_router,
    prefix="/api/v1/admin/inventory",
)

app.include_router(
    inventory_balance_router,
    prefix="/api/v1/admin/inventory",
)

app.include_router(
    inventory_reservation_router,
    prefix="/api/v1/admin/inventory",
)

app.include_router(
    inventory_movement_router,
    prefix="/api/v1/admin/inventory",
)

app.include_router(
    stock_adjustment_router,
    prefix="/api/v1/admin/inventory",
)


# ------------------------------------------------------------
# ADMIN - COUPONS
# ------------------------------------------------------------

app.include_router(admin_coupon_router, prefix="/api/v1")


# ------------------------------------------------------------
# AFFILIATE - APPLICATIONS & ADMIN
# ------------------------------------------------------------

app.include_router(affiliate_admin_router, prefix="/api/v1")
app.include_router(affiliates_admin_router, prefix="/api/v1")
app.include_router(affiliate_public_router, prefix="/api/v1")


# ------------------------------------------------------------
# AFFILIATE - AUTHENTICATION
# ------------------------------------------------------------

app.include_router(affiliate_auth_router, prefix="/api/v1")

app.include_router(
    affiliate_activation_admin_router,
    prefix="/api/v1",
)
app.include_router(
    affiliate_referral_router,
    prefix="/api/v1",
)


# ------------------------------------------------------------
# SHOP - CATALOG
# ------------------------------------------------------------

app.include_router(
    category_router,
    prefix="/api/v1/catalog",
)

app.include_router(
    subcategory_router,
    prefix="/api/v1/catalog",
)

app.include_router(
    product_router,
    prefix="/api/v1/catalog",
)

app.include_router(
    product_image_router,
    prefix="/api/v1/catalog",
)

app.include_router(
    variant_router,
    prefix="/api/v1/catalog",
)


# ------------------------------------------------------------
# SHOP - CART
# ------------------------------------------------------------

app.include_router(
    guest_cart_router,
    prefix="/api/v1/shop",
)

app.include_router(
    customer_cart_router,
    prefix="/api/v1/shop",
)


# ------------------------------------------------------------
# SHOP - CUSTOMER AUTHENTICATION & PROFILE
# ------------------------------------------------------------

app.include_router(
    customer_auth_router,
    prefix="/api/v1/shop",
)

app.include_router(
    customer_forgot_password_router,
    prefix="/api/v1/shop",
)

app.include_router(
    customer_otp_router,
    prefix="/api/v1/shop",
)

app.include_router(
    profile_router,
    prefix="/api/v1/shop",
)

app.include_router(
    customer_address_router,
    prefix="/api/v1/shop",
)

app.include_router(
    customer_wishlist_router,
    prefix="/api/v1/shop",
)

app.include_router(
    customer_notifications_router,
    prefix="/api/v1",
)

app.include_router(
    shipping_webhook_router,
    prefix="/api/v1",
)


# ------------------------------------------------------------
# SHOP - COUPONS
# ------------------------------------------------------------

app.include_router(
    customer_coupon_router,
    prefix="/api/v1/shop",
)


# ------------------------------------------------------------
# SHOP - CHECKOUT, ORDERS & PAYMENTS
# ------------------------------------------------------------

app.include_router(
    checkout_router,
    prefix="/api/v1/shop",
)

app.include_router(
    order_router,
    prefix="/api/v1/shop",
)

app.include_router(
    payment_router,
    prefix="/api/v1/shop",
)

app.include_router(
    refund_router,
    prefix="/api/v1/shop",
)


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/", tags=["Health"])
def root():
    return {
        "message": "EnergyMax API is running."
    }
