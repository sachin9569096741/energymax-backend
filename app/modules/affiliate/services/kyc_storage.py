
from __future__ import annotations

import hashlib
import importlib
import os
import io
import time
import urllib.error
import urllib.request
from pathlib import Path
from uuid import uuid4

MAX_KYC_FILE_SIZE = 5 * 1024 * 1024

ALLOWED_DOCUMENTS = {
    "AADHAAR_FRONT",
    "AADHAAR_BACK",
    "PAN_CARD",
}

ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
}


class KYCStorageError(Exception):
    pass


def detect_file_type(data: bytes) -> str:
    """Validate the basic signature of an uploaded document."""

    if data.startswith(b"%PDF-"):
        return "application/pdf"

    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"

    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"

    raise KYCStorageError(
        "Unsupported or invalid file content. "
        "Upload a valid PDF, JPEG, or PNG."
    )


def validate_storage_key(storage_key: str) -> str:
    """Accept only server-generated storage keys."""

    if (
        not storage_key
        or "/" in storage_key
        or "\\" in storage_key
        or storage_key in {".", ".."}
        or Path(storage_key).name != storage_key
    ):
        raise KYCStorageError("Invalid storage key.")

    return storage_key


class LocalDevelopmentKYCStorage:
    """Private filesystem storage for local development only."""

    def __init__(self) -> None:
        environment = os.getenv(
            "APP_ENV",
            "development",
        ).lower()

        if environment in {"production", "prod"}:
            raise KYCStorageError(
                "Local KYC storage is disabled in production."
            )

        configured_path = os.getenv(
            "KYC_LOCAL_STORAGE_DIR",
            ".private_kyc_storage",
        )

        self.root = Path(configured_path).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, data: bytes) -> str:
        if not data:
            raise KYCStorageError("The uploaded file is empty.")

        if len(data) > MAX_KYC_FILE_SIZE:
            raise KYCStorageError(
                "The file exceeds the 5 MB limit."
            )

        detect_file_type(data)

        storage_key = f"{uuid4().hex}.bin"
        destination = self.root / storage_key

        with destination.open("xb") as file:
            file.write(data)

        return storage_key

    def read(self, storage_key: str) -> bytes:
        storage_key = validate_storage_key(storage_key)
        destination = (self.root / storage_key).resolve()

        if destination.parent != self.root:
            raise KYCStorageError("Invalid storage path.")

        if not destination.is_file():
            raise KYCStorageError("Document not found.")

        return destination.read_bytes()

    def delete(self, storage_key: str) -> None:
        storage_key = validate_storage_key(storage_key)
        destination = (self.root / storage_key).resolve()

        if destination.parent != self.root:
            raise KYCStorageError("Invalid storage path.")

        destination.unlink(missing_ok=True)


class S3PrivateKYCStorage:
    """
    Private S3-compatible object storage.

    Objects are accessed through the backend, not public URLs.
    """

    def __init__(self) -> None:
        try:
            boto3 = importlib.import_module("boto3")
            Config = importlib.import_module("botocore.config").Config
        except ImportError as exc:
            raise KYCStorageError(
                "S3 storage dependency is missing. "
                "Install boto3 before enabling S3 storage."
            ) from exc

        bucket = os.getenv("KYC_S3_BUCKET")
        region = os.getenv("AWS_REGION")

        if not bucket or not region:
            raise KYCStorageError(
                "KYC_S3_BUCKET and AWS_REGION must be configured."
            )

        endpoint_url = os.getenv("KYC_S3_ENDPOINT_URL") or None

        # Use the Render service's IAM role where available, or
        # credentials supplied through the AWS credential chain.
        # Never embed credentials in source code.
        self.client = boto3.client(
            "s3",
            region_name=region,
            endpoint_url=endpoint_url,
            config=Config(
                signature_version="s3v4",
                retries={"max_attempts": 3, "mode": "standard"},
            ),
        )

        self.bucket = bucket
        self.prefix = "kyc-private"

    def _object_key(self, storage_key: str) -> str:
        storage_key = validate_storage_key(storage_key)
        return f"{self.prefix}/{storage_key}"

    def save(self, data: bytes) -> str:
        if not data:
            raise KYCStorageError("The uploaded file is empty.")

        if len(data) > MAX_KYC_FILE_SIZE:
            raise KYCStorageError(
                "The file exceeds the 5 MB limit."
            )

        content_type = detect_file_type(data)
        storage_key = f"{uuid4().hex}.bin"

        try:
            self.client.put_object(
                Bucket=self.bucket,
                Key=self._object_key(storage_key),
                Body=data,
                ContentType=content_type,
                ServerSideEncryption="AES256",
            )
        except Exception as exc:
            # Log the original exception securely at the service layer.
            raise KYCStorageError(
                "Unable to store the private KYC document."
            ) from exc

        return storage_key

    def read(self, storage_key: str) -> bytes:
        try:
            response = self.client.get_object(
                Bucket=self.bucket,
                Key=self._object_key(storage_key),
            )

            body = response["Body"]

            try:
                data = body.read(MAX_KYC_FILE_SIZE + 1)
            finally:
                body.close()

            if len(data) > MAX_KYC_FILE_SIZE:
                raise KYCStorageError(
                    "Stored document exceeds the permitted size."
                )

            if not data:
                raise KYCStorageError(
                    "The stored document is empty."
                )

            return data

        except KYCStorageError:
            raise
        except Exception as exc:
            raise KYCStorageError(
                "Unable to retrieve the private document."
            ) from exc

    def delete(self, storage_key: str) -> None:
        try:
            self.client.delete_object(
                Bucket=self.bucket,
                Key=self._object_key(storage_key),
            )
        except Exception as exc:
            raise KYCStorageError(
                "Unable to delete the private KYC document."
            ) from exc

class CloudinaryPrivateKYCStorage:
    """
    Cloudinary authenticated storage for private KYC documents.

    Storage keys contain only server-generated filenames.
    Cloudinary public IDs are constructed internally.

    Documents are uploaded as authenticated raw assets.
    Downloads are performed server-side using short-lived URLs.
    """

    PREFIX = "kyc-private"

    def __init__(self) -> None:
        try:
            self.cloudinary = importlib.import_module("cloudinary")
            self.uploader = importlib.import_module(
                "cloudinary.uploader"
            )
            self.utils = importlib.import_module("cloudinary.utils")
        except ImportError as exc:
            raise KYCStorageError(
                "Cloudinary SDK is not installed."
            ) from exc

        cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
        api_key = os.getenv("CLOUDINARY_API_KEY")
        api_secret = os.getenv("CLOUDINARY_API_SECRET")

        if not all([cloud_name, api_key, api_secret]):
            raise KYCStorageError(
                "Cloudinary credentials are not configured."
            )

        try:
            self.cloudinary.config(
                cloud_name=cloud_name,
                api_key=api_key,
                api_secret=api_secret,
                secure=True,
            )
        except Exception as exc:
            raise KYCStorageError(
                "Unable to configure private document storage."
            ) from exc

    def _public_id(self, storage_key: str) -> str:
        storage_key = validate_storage_key(storage_key)

        return f"{self.PREFIX}/{storage_key}"

    @staticmethod
    def _extension(content_type: str) -> str:
        extensions = {
            "application/pdf": "pdf",
            "image/jpeg": "jpg",
            "image/png": "png",
        }

        try:
            return extensions[content_type]
        except KeyError as exc:
            raise KYCStorageError(
                "Unsupported KYC document format."
            ) from exc

    def save(self, data: bytes) -> str:
        if not data:
            raise KYCStorageError(
                "The uploaded file is empty."
            )

        if len(data) > MAX_KYC_FILE_SIZE:
            raise KYCStorageError(
                "The file exceeds the 5 MB limit."
            )

        content_type = detect_file_type(data)
        extension = self._extension(content_type)

        # Raw assets use an identifier with a file extension.
        storage_key = f"{uuid4().hex}.{extension}"
        public_id = self._public_id(storage_key)

        try:
            result = self.uploader.upload(
                io.BytesIO(data),
                resource_type="raw",
                type="authenticated",
                public_id=public_id,
                overwrite=False,
                unique_filename=False,
            )

            # Do not silently accept an unexpected resource type
            # or delivery type.
            if result.get("resource_type") != "raw":
                raise KYCStorageError(
                    "Cloudinary returned an unexpected resource type."
                )

            if result.get("type") != "authenticated":
                raise KYCStorageError(
                    "Cloudinary did not confirm authenticated delivery."
                )

            return storage_key

        except KYCStorageError:
            raise
        except Exception as exc:
            raise KYCStorageError(
                "Unable to store the private KYC document."
            ) from exc

    def read(self, storage_key: str) -> bytes:
        public_id = self._public_id(storage_key)

        # The extension is included in the raw asset's public ID.
        extension = storage_key.rsplit(".", 1)[-1].lower()

        if extension not in {"pdf", "jpg", "png"}:
            raise KYCStorageError(
                "Invalid stored document format."
            )

        try:
            download_url = self.utils.private_download_url(
                public_id,
                extension,
                resource_type="raw",
                type="authenticated",
                expires_at=int(time.time()) + 60,
            )

            # Retrieve the file on the backend. Never return the
            # signed URL to the client.
            request = urllib.request.Request(
                download_url,
                headers={"User-Agent": "EnergyMax-KYC-Backend"},
            )

            with urllib.request.urlopen(
                request,
                timeout=20,
            ) as response:
                data = response.read(MAX_KYC_FILE_SIZE + 1)

            if not data:
                raise KYCStorageError(
                    "The stored document is empty."
                )

            if len(data) > MAX_KYC_FILE_SIZE:
                raise KYCStorageError(
                    "Stored document exceeds the permitted size."
                )

            # Validate downloaded bytes rather than trusting the
            # extension or remote response headers.
            detect_file_type(data)

            return data

        except KYCStorageError:
            raise
        except Exception as exc:
            raise KYCStorageError(
                "Unable to retrieve the private document."
            ) from exc

    def delete(self, storage_key: str) -> None:
        public_id = self._public_id(storage_key)

        try:
            result = self.uploader.destroy(
                public_id,
                resource_type="raw",
                type="authenticated",
                invalidate=True,
            )

            if result.get("result") not in {
                "ok",
                "not found",
            }:
                raise KYCStorageError(
                    "Cloudinary could not confirm document deletion."
                )

        except KYCStorageError:
            raise
        except Exception as exc:
            raise KYCStorageError(
                "Unable to delete the private KYC document."
            ) from exc

def get_kyc_storage():
    """
    Select the configured KYC storage backend.

    Production never silently falls back to local storage.
    """

    environment = os.getenv(
        "APP_ENV",
        "development",
    ).lower()

    backend = os.getenv(
        "KYC_STORAGE_BACKEND",
        "local",
    ).lower()

    if backend == "cloudinary":
        return CloudinaryPrivateKYCStorage()

    if backend == "s3":
        return S3PrivateKYCStorage()

    if backend == "local" and environment not in {
        "production",
        "prod",
    }:
        return LocalDevelopmentKYCStorage()

    raise KYCStorageError(
        "Private KYC storage is not configured for this environment."
    )


def calculate_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
