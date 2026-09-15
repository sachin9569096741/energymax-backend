from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.shop.catalog.schemas.product_image import (
    ProductImageResponse,
)
from app.modules.shop.catalog.services.product_image import (
    ProductImageService,
)


router = APIRouter(
    prefix="/product-images",
    tags=["Shop - Product Images"],
)


# ---------------------------------------------------------
# Upload product image
# ---------------------------------------------------------

@router.post(
    "",
    response_model=ProductImageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_product_image(
    product_id: int = Form(..., gt=0),
    file: UploadFile = File(...),
    alt_text: str | None = Form(default=None),
    display_order: int = Form(default=0, ge=0),
    is_primary: bool = Form(default=False),
    db: Session = Depends(get_db),
):
    service = ProductImageService(db)

    try:
        image = await service.create_image(
            product_id=product_id,
            file=file,
            alt_text=alt_text,
            display_order=display_order,
            is_primary=is_primary,
        )

        db.commit()
        db.refresh(image)

        return image

    except ValueError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


# ---------------------------------------------------------
# List product images
# ---------------------------------------------------------

@router.get(
    "",
    response_model=list[ProductImageResponse],
)
def list_product_images(
    product_id: int,
    db: Session = Depends(get_db),
):
    service = ProductImageService(db)

    try:
        return service.list_images(
            product_id=product_id,
            active_only=True,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


# ---------------------------------------------------------
# Get image
# ---------------------------------------------------------

@router.get(
    "/{public_id}",
    response_model=ProductImageResponse,
)
def get_product_image(
    public_id: str,
    db: Session = Depends(get_db),
):
    service = ProductImageService(db)

    try:
        return service.get_image(
            public_id=public_id,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


# ---------------------------------------------------------
# Set primary image
# ---------------------------------------------------------

@router.patch(
    "/{public_id}/primary",
    response_model=ProductImageResponse,
)
def set_primary_product_image(
    public_id: str,
    db: Session = Depends(get_db),
):
    service = ProductImageService(db)

    try:
        image = service.set_primary_image(
            public_id=public_id,
        )

        db.commit()
        db.refresh(image)

        return image

    except ValueError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


# ---------------------------------------------------------
# Delete image
# ---------------------------------------------------------

@router.delete(
    "/{public_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_product_image(
    public_id: str,
    db: Session = Depends(get_db),
):
    service = ProductImageService(db)

    try:
        service.delete_image(
            public_id=public_id,
        )

        db.commit()

    except ValueError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )