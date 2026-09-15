from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.shop.catalog.schemas.subcategory import (
    SubcategoryCreate,
    SubcategoryResponse,
    SubcategoryUpdate,
)
from app.modules.shop.catalog.services.subcategory import (
    SubcategoryService,
)


router = APIRouter(
    prefix="/subcategories",
    tags=["Catalog - Subcategories"],
)


# ------------------------------------------------------------------
# CREATE
# ------------------------------------------------------------------

@router.post(
    "",
    response_model=SubcategoryResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_subcategory(
    payload: SubcategoryCreate,
    db: Session = Depends(get_db),
):
    service = SubcategoryService(db)

    try:
        subcategory = service.create_subcategory(
            category_public_id=payload.category_public_id,
            name=payload.name,
            slug=payload.slug,
            description=payload.description,
            image_url=payload.image_url,
            display_order=payload.display_order,
            is_active=payload.is_active,
        )

        db.commit()
        db.refresh(subcategory)

        return subcategory

    except ValueError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


# ------------------------------------------------------------------
# GET BY PUBLIC ID
# ------------------------------------------------------------------

@router.get(
    "/{public_id}",
    response_model=SubcategoryResponse,
)
def get_subcategory(
    public_id: str,
    db: Session = Depends(get_db),
):
    service = SubcategoryService(db)

    try:
        return service.get_subcategory(
            public_id=public_id,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


# ------------------------------------------------------------------
# LIST BY CATEGORY PUBLIC ID
# ------------------------------------------------------------------

@router.get(
    "/category/{category_public_id}",
    response_model=list[SubcategoryResponse],
)
def list_subcategories(
    category_public_id: str,
    active_only: bool = True,
    db: Session = Depends(get_db),
):
    service = SubcategoryService(db)

    try:
        items, total = service.list_subcategories(
            category_public_id=category_public_id,
            is_active=active_only,
        )

        return items

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


# ------------------------------------------------------------------
# UPDATE
# ------------------------------------------------------------------

@router.patch(
    "/{public_id}",
    response_model=SubcategoryResponse,
)
def update_subcategory(
    public_id: str,
    payload: SubcategoryUpdate,
    db: Session = Depends(get_db),
):
    service = SubcategoryService(db)

    try:
        data = payload.model_dump(
            exclude_unset=True,
        )

        subcategory = service.update_subcategory(
            public_id=public_id,
            data=data,
        )

        db.commit()
        db.refresh(subcategory)

        return subcategory

    except ValueError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


# ------------------------------------------------------------------
# DELETE
# ------------------------------------------------------------------

@router.delete(
    "/{public_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_subcategory(
    public_id: str,
    db: Session = Depends(get_db),
):
    service = SubcategoryService(db)

    try:
        service.delete_subcategory(
            public_id=public_id,
        )

        db.commit()

    except ValueError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )