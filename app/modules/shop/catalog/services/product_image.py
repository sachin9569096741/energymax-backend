from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.modules.shop.catalog.models.product_image import ProductImage
from app.modules.shop.catalog.repositories.product import ProductRepository
from app.modules.shop.catalog.repositories.product_image import (
    ProductImageRepository,
)
from app.modules.shop.catalog.services.image_upload import (
    ImageUploadService,
)


class ProductImageService:

    MAX_IMAGES_PER_PRODUCT = 5

    def __init__(self, db: Session):
        self.product_repository = ProductRepository(db)
        self.image_repository = ProductImageRepository(db)
        self.image_upload_service = ImageUploadService()

    # ---------------------------------------------------------
    # Create image
    # ---------------------------------------------------------

    async def create_image(
        self,
        *,
        product_id: int,
        file: UploadFile,
        alt_text: str | None = None,
        display_order: int = 0,
        is_primary: bool = False,
        is_active: bool = True,
    ) -> ProductImage:

        # -----------------------------------------------------
        # 1. Validate product
        # -----------------------------------------------------

        product = self.product_repository.get_by_id(
            product_id
        )

        if product is None:
            raise ValueError(
                f"Product with id '{product_id}' does not exist."
            )

        # -----------------------------------------------------
        # 2. Validate image limit
        # -----------------------------------------------------

        existing_count = (
            self.image_repository.count_by_product_id(
                product_id,
                active_only=True,
            )
        )

        if existing_count >= self.MAX_IMAGES_PER_PRODUCT:
            raise ValueError(
                f"A product can have a maximum of "
                f"{self.MAX_IMAGES_PER_PRODUCT} active images."
            )

        # -----------------------------------------------------
        # 3. Upload image to Cloudinary
        # -----------------------------------------------------

        upload_result = (
            await self.image_upload_service.upload_product_image(
                file,
                product_public_id=product.public_id,
            )
        )

        image_url = upload_result["image_url"]
        cloudinary_public_id = upload_result[
            "cloudinary_public_id"
        ]

        # -----------------------------------------------------
        # 4. Primary image handling
        # -----------------------------------------------------

        # If this is the first image, automatically make it
        # primary even when is_primary=False was supplied.

        if existing_count == 0:
            is_primary = True

        elif is_primary:
            self._unset_primary_images(product_id)

        # -----------------------------------------------------
        # 5. Create database record
        # -----------------------------------------------------

        image = ProductImage(
            product_id=product_id,
            image_url=image_url,
            cloudinary_public_id=cloudinary_public_id,
            alt_text=alt_text,
            display_order=display_order,
            is_primary=is_primary,
            is_active=is_active,
        )

        # -----------------------------------------------------
        # 6. Persist
        # -----------------------------------------------------

        try:
            return self.image_repository.create(image)

        except Exception:
            # Database failed after Cloudinary upload.
            # Remove the uploaded Cloudinary asset so we don't
            # leave an orphaned image.

            self.image_upload_service.delete_product_image(
                cloudinary_public_id
            )

            raise

    # ---------------------------------------------------------
    # Get image
    # ---------------------------------------------------------

    def get_image(
        self,
        *,
        public_id: str,
    ) -> ProductImage:

        image = self.image_repository.get_by_public_id(
            public_id
        )

        if image is None:
            raise ValueError(
                f"Product image with public_id "
                f"'{public_id}' does not exist."
            )

        return image

    # ---------------------------------------------------------
    # List product images
    # ---------------------------------------------------------

    def list_images(
        self,
        *,
        product_id: int,
        active_only: bool = True,
    ) -> list[ProductImage]:

        # -----------------------------------------------------
        # Validate product
        # -----------------------------------------------------

        product = self.product_repository.get_by_id(
            product_id
        )

        if product is None:
            raise ValueError(
                f"Product with id '{product_id}' does not exist."
            )

        # -----------------------------------------------------
        # Get images
        # -----------------------------------------------------

        return self.image_repository.get_by_product_id(
            product_id,
            active_only=active_only,
        )

    # ---------------------------------------------------------
    # Update image
    # ---------------------------------------------------------

    def update_image(
        self,
        *,
        public_id: str,
        data: dict,
    ) -> ProductImage:

        image = self.image_repository.get_by_public_id(
            public_id
        )

        if image is None:
            raise ValueError(
                f"Product image with public_id "
                f"'{public_id}' does not exist."
            )

        # -----------------------------------------------------
        # Primary image handling
        # -----------------------------------------------------

        if data.get("is_primary") is True:

            if not image.is_active:
                raise ValueError(
                    "An inactive image cannot be set as primary."
                )

            self._unset_primary_images(
                image.product_id
            )

        # -----------------------------------------------------
        # Prevent inactive primary image
        # -----------------------------------------------------

        if data.get("is_active") is False:
            data["is_primary"] = False

        # -----------------------------------------------------
        # Update
        # -----------------------------------------------------

        return self.image_repository.update(
            image,
            data,
        )

    # ---------------------------------------------------------
    # Set primary image
    # ---------------------------------------------------------

    def set_primary_image(
        self,
        *,
        public_id: str,
    ) -> ProductImage:

        image = self.image_repository.get_by_public_id(
            public_id
        )

        if image is None:
            raise ValueError(
                f"Product image with public_id "
                f"'{public_id}' does not exist."
            )

        if not image.is_active:
            raise ValueError(
                "An inactive image cannot be set as primary."
            )

        # -----------------------------------------------------
        # Remove primary from all other images
        # -----------------------------------------------------

        self._unset_primary_images(
            image.product_id
        )

        # -----------------------------------------------------
        # Set selected image as primary
        # -----------------------------------------------------

        image.is_primary = True

        return self.image_repository.update(
            image,
            {},
        )

    # ---------------------------------------------------------
    # Delete image
    # ---------------------------------------------------------

    def delete_image(
        self,
        *,
        public_id: str,
    ) -> None:

        image = self.image_repository.get_by_public_id(
            public_id
        )

        if image is None:
            raise ValueError(
                f"Product image with public_id "
                f"'{public_id}' does not exist."
            )

        cloudinary_public_id = (
            image.cloudinary_public_id
        )

        was_primary = image.is_primary

        product_id = image.product_id

        # -----------------------------------------------------
        # Delete from Cloudinary first
        # -----------------------------------------------------

        try:
            self.image_upload_service.delete_product_image(
                cloudinary_public_id
            )

        except Exception as exc:
            raise ValueError(
                "Failed to delete image from Cloudinary."
            ) from exc

        # -----------------------------------------------------
        # Delete database record
        # -----------------------------------------------------

        self.image_repository.delete(image)

        # -----------------------------------------------------
        # If primary image was deleted, promote another image
        # -----------------------------------------------------

        if was_primary:

            remaining_images = (
                self.image_repository.get_by_product_id(
                    product_id,
                    active_only=True,
                )
            )

            if remaining_images:
                next_image = remaining_images[0]
                next_image.is_primary = True

                self.image_repository.update(
                    next_image,
                    {},
                )

    # ---------------------------------------------------------
    # Internal helper
    # ---------------------------------------------------------

    def _unset_primary_images(
        self,
        product_id: int,
    ) -> None:

        images = self.image_repository.get_by_product_id(
            product_id,
            active_only=False,
        )

        for image in images:
            if image.is_primary:
                image.is_primary = False

        # The repository's update() is not needed for each image
        # because these are already tracked SQLAlchemy objects.
        self._flush()

    # ---------------------------------------------------------
    # Internal database helper
    # ---------------------------------------------------------

    def _flush(self) -> None:
        """
        Flush pending SQLAlchemy changes.

        The repository doesn't expose a dedicated flush method,
        so this helper intentionally remains internal to the
        service.
        """
        self.image_repository.db.flush()