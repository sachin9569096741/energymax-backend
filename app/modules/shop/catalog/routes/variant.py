from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.admin.auth.security.dependencies import (
    require_permission,
)
from app.modules.shop.catalog.repositories.product import ProductRepository
from app.modules.shop.catalog.schemas.variant import (
    VariantCreate,
    VariantListResponse,
    VariantResponse,
    VariantUpdate,
)
from app.modules.shop.catalog.services.variant import VariantService


router = APIRouter(
    prefix="/products",
    tags=["Shop - Product Variants"],
)


# ============================================================
# PUBLIC: List Product Variants
# ============================================================

@router.get(
    "/{product_public_id}/variants",
    response_model=VariantListResponse,
)
def list_variants(
    product_public_id: str,
    db: Session = Depends(get_db),
):
    product_repository = ProductRepository(db)

    product = product_repository.get_by_public_id(
        product_public_id
    )

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    service = VariantService(db)

    variants = service.list_variants(
        product_id=product.id,
        active_only=True,
    )

    return VariantListResponse(
        items=variants,
        total=len(variants),
    )


# ============================================================
# ADMIN: Create Product Variant
# ============================================================

@router.post(
    "/{product_public_id}/variants",
    response_model=VariantResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(
            require_permission(
                permission_name="create_product"
            )
        )
    ],
)
def create_variant(
    product_public_id: str,
    payload: VariantCreate,
    db: Session = Depends(get_db),
):
    product_repository = ProductRepository(db)

    product = product_repository.get_by_public_id(
        product_public_id
    )

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    service = VariantService(db)

    try:
        variant = service.create_variant(
            product_id=product.id,
            **payload.model_dump(),
        )

        db.commit()

        return variant

    except ValueError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


# ============================================================
# PUBLIC: Get Single Variant
# ============================================================

@router.get(
    "/variants/{public_id}",
    response_model=VariantResponse,
)
def get_variant(
    public_id: str,
    db: Session = Depends(get_db),
):
    service = VariantService(db)

    try:
        return service.get_variant(
            public_id=public_id,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


# ============================================================
# ADMIN: Update Variant
# ============================================================

@router.patch(
    "/variants/{public_id}",
    response_model=VariantResponse,
    dependencies=[
        Depends(
            require_permission(
                permission_name="update_product"
            )
        )
    ],
)
def update_variant(
    public_id: str,
    payload: VariantUpdate,
    db: Session = Depends(get_db),
):
    service = VariantService(db)

    data = payload.model_dump(
        exclude_unset=True
    )

    try:
        variant = service.update_variant(
            public_id=public_id,
            data=data,
        )

        db.commit()

        return variant

    except ValueError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


# ============================================================
# ADMIN: Delete Variant
# ============================================================

@router.delete(
    "/variants/{public_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[
        Depends(
            require_permission(
                permission_name="delete_product"
            )
        )
    ],
)
def delete_variant(
    public_id: str,
    db: Session = Depends(get_db),
):
    service = VariantService(db)

    try:
        service.delete_variant(
            public_id=public_id,
        )

        db.commit()

    except ValueError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )