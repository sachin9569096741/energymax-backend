from fastapi import APIRouter

from app.modules.shop.catalog.routes.category import (
    router as category_router,
)
from app.modules.shop.catalog.routes.product import (
    router as product_router,
)
from app.modules.shop.catalog.routes.product_image import (
    router as product_image_router,
)
from app.modules.shop.catalog.routes.subcategory import (
    router as subcategory_router,
)
from app.modules.shop.catalog.routes.variant import (
    router as variant_router,
)


router = APIRouter()

router.include_router(
    category_router,
)

router.include_router(
    subcategory_router,
)

router.include_router(
    product_router,
)

router.include_router(
    product_image_router,
)

router.include_router(
    variant_router,
)