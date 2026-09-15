from io import BytesIO

import cloudinary.uploader
from fastapi import UploadFile


class ImageUploadService:

    ALLOWED_CONTENT_TYPES = {
        "image/jpeg",
        "image/png",
        "image/webp",
    }

    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

    # ---------------------------------------------------------
    # Upload product image
    # ---------------------------------------------------------

    async def upload_product_image(
        self,
        file: UploadFile,
        *,
        product_public_id: str,
    ) -> dict[str, str]:

        # -----------------------------------------------------
        # 1. Validate content type
        # -----------------------------------------------------

        if file.content_type not in self.ALLOWED_CONTENT_TYPES:
            raise ValueError(
                "Unsupported image type. "
                "Allowed types: JPEG, PNG, WEBP."
            )

        # -----------------------------------------------------
        # 2. Read file
        # -----------------------------------------------------

        contents = await file.read()

        if not contents:
            raise ValueError(
                "Uploaded image is empty."
            )

        # -----------------------------------------------------
        # 3. Validate file size
        # -----------------------------------------------------

        if len(contents) > self.MAX_FILE_SIZE:
            raise ValueError(
                "Image size cannot exceed 5 MB."
            )

        # -----------------------------------------------------
        # 4. Upload to Cloudinary
        # -----------------------------------------------------

        try:

            result = cloudinary.uploader.upload(
                BytesIO(contents),
                folder=f"energymax/products/{product_public_id}",
                resource_type="image",
            )

        except Exception as exc:

            # Print the REAL Cloudinary error in backend terminal
            print(
                "CLOUDINARY UPLOAD ERROR:",
                repr(exc),
            )

            raise ValueError(
                f"Failed to upload image to Cloudinary: {exc}"
            ) from exc

        # -----------------------------------------------------
        # 5. Validate Cloudinary response
        # -----------------------------------------------------

        if not result.get("secure_url"):
            raise ValueError(
                "Cloudinary upload succeeded but "
                "no secure URL was returned."
            )

        if not result.get("public_id"):
            raise ValueError(
                "Cloudinary upload succeeded but "
                "no public ID was returned."
            )

        # -----------------------------------------------------
        # 6. Return Cloudinary information
        # -----------------------------------------------------

        return {
            "image_url": result["secure_url"],
            "cloudinary_public_id": result["public_id"],
        }

    # ---------------------------------------------------------
    # Delete product image from Cloudinary
    # ---------------------------------------------------------

    def delete_product_image(
        self,
        cloudinary_public_id: str,
    ) -> None:

        if not cloudinary_public_id:
            raise ValueError(
                "Cloudinary public ID is required."
            )

        try:

            result = cloudinary.uploader.destroy(
                cloudinary_public_id,
                resource_type="image",
                invalidate=True,
            )

        except Exception as exc:

            print(
                "CLOUDINARY DELETE ERROR:",
                repr(exc),
            )

            raise ValueError(
                "Failed to delete image from Cloudinary."
            ) from exc

        if result.get("result") not in {
            "ok",
            "not found",
        }:
            raise ValueError(
                "Cloudinary failed to delete the image."
            )