from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.modules.admin.auth.security.dependencies import (
    require_permission,
)
from app.db.session import get_db
from app.modules.shop.catalog.schemas.product import (
    ProductCreate,
    ProductListResponse,
    ProductResponse,
    ProductUpdate,
)
from app.modules.shop.catalog.services.product import ProductService


router = APIRouter(
    prefix="/products",
    tags=["Shop - Products"],
)


@router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(
            require_permission(
                permission_name="create_product"
            )
        )
    ],
)
def create_product(
    payload: ProductCreate,
    db: Session = Depends(get_db),
):
    service = ProductService(db)

    try:
        product = service.create_product(
            **payload.model_dump()
        )

        db.commit()

        return product

    except ValueError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.get(
    "",
    response_model=ProductListResponse,
    dependencies=[
        Depends(
            require_permission(
                permission_name="view_products"
            )
        )
    ],
)
def list_products(
    subcategory_id: int | None = Query(
        default=None,
        gt=0,
    ),
    is_active: bool | None = True,
    is_featured: bool | None = None,
    page: int = Query(
        default=1,
        ge=1,
    ),
    page_size: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
    db: Session = Depends(get_db),
):
    service = ProductService(db)

    try:
        products, total = service.list_products(
            subcategory_id=subcategory_id,
            is_active=is_active,
            is_featured=is_featured,
            page=page,
            page_size=page_size,
        )

        return ProductListResponse(
            items=products,
            total=total,
            page=page,
            page_size=page_size,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.get(
    "/{public_id}",
    response_model=ProductResponse,
    dependencies=[
        Depends(
            require_permission(
                permission_name="view_products"
            )
        )
    ],
)
def get_product(
    public_id: str,
    db: Session = Depends(get_db),
):
    service = ProductService(db)

    try:
        return service.get_product(
            public_id=public_id
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


@router.patch(
    "/{public_id}",
    response_model=ProductResponse,
    dependencies=[
        Depends(
            require_permission(
                permission_name="update_product"
            )
        )
    ],
)
def update_product(
    public_id: str,
    payload: ProductUpdate,
    db: Session = Depends(get_db),
):
    service = ProductService(db)

    data = payload.model_dump(
        exclude_unset=True
    )

    try:
        product = service.update_product(
            public_id=public_id,
            data=data,
        )

        db.commit()

        return product

    except ValueError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.delete(
    "/{public_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[
        Depends(
            require_permission(
                permission_name="delete_product"
            )
        )
    ],
)
def delete_product(
    public_id: str,
    db: Session = Depends(get_db),
):
    service = ProductService(db)

    try:
        service.delete_product(
            public_id=public_id
        )

        db.commit()

    except ValueError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )