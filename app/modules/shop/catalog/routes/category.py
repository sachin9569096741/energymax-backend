from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.shop.catalog.schemas.category import (
    CategoryCreate,
    CategoryListResponse,
    CategoryResponse,
    CategoryUpdate,
)
from app.modules.shop.catalog.services.category import CategoryService


router = APIRouter(
    prefix="/categories",
    tags=["Shop - Categories"],
)


# ---------------------------------------------------------
# CREATE
# ---------------------------------------------------------


@router.post(
    "",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_category(
    payload: CategoryCreate,
    db: Session = Depends(get_db),
):
    service = CategoryService(db)

    try:
        category = service.create_category(
            **payload.model_dump()
        )

        db.commit()

        return category

    except ValueError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


# ---------------------------------------------------------
# LIST
# ---------------------------------------------------------


@router.get(
    "",
    response_model=CategoryListResponse,
)
def list_categories(
    is_active: bool | None = True,
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
    service = CategoryService(db)

    try:
        categories, total = service.list_categories(
            is_active=is_active,
            page=page,
            page_size=page_size,
        )

        return CategoryListResponse(
            items=categories,
            total=total,
            page=page,
            page_size=page_size,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


# ---------------------------------------------------------
# GET
# ---------------------------------------------------------


@router.get(
    "/{public_id}",
    response_model=CategoryResponse,
)
def get_category(
    public_id: str,
    db: Session = Depends(get_db),
):
    service = CategoryService(db)

    try:
        return service.get_category(
            public_id=public_id
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


# ---------------------------------------------------------
# UPDATE
# ---------------------------------------------------------


@router.patch(
    "/{public_id}",
    response_model=CategoryResponse,
)
def update_category(
    public_id: str,
    payload: CategoryUpdate,
    db: Session = Depends(get_db),
):
    service = CategoryService(db)

    data = payload.model_dump(
        exclude_unset=True
    )

    try:
        category = service.update_category(
            public_id=public_id,
            data=data,
        )

        db.commit()

        return category

    except ValueError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


# ---------------------------------------------------------
# DELETE
# ---------------------------------------------------------


@router.delete(
    "/{public_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_category(
    public_id: str,
    db: Session = Depends(get_db),
):
    service = CategoryService(db)

    try:
        service.delete_category(
            public_id=public_id
        )

        db.commit()

    except ValueError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )