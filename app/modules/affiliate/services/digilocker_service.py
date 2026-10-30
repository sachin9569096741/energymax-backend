import logging
import re
import uuid
from typing import Any

import httpx

from app.core.config import settings


logger = logging.getLogger(__name__)


class DigiLockerServiceError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(message)


class DigiLockerService:
    TIMEOUT = 20.0
    DOCUMENT_TYPES = {"AADHAAR", "PAN", "DRIVING_LICENSE"}

    def __init__(self):
        environment = str(
            settings.cashfree_verification_environment
        ).strip().lower()

        if environment in {"sandbox", "test", "testing"}:
            self.base_url = "https://sandbox.cashfree.com/verification"
        elif environment in {"production", "prod", "live"}:
            self.base_url = "https://api.cashfree.com/verification"
        else:
            raise RuntimeError(
                "Invalid CASHFREE_VERIFICATION_ENVIRONMENT setting."
            )

        self.client_id = settings.cashfree_verification_client_id
        self.client_secret = settings.cashfree_verification_client_secret

        if not self.client_id or not self.client_secret:
            raise RuntimeError(
                "Cashfree verification credentials are not configured."
            )

    @property
    def headers(self) -> dict[str, str]:
        return {
            "x-client-id": self.client_id,
            "x-client-secret": self.client_secret,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def _request(
        self,
        method: str,
        endpoint: str,
        *,
        payload: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        try:
            async with httpx.AsyncClient(
                timeout=self.TIMEOUT,
                follow_redirects=False,
            ) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=self.headers,
                    json=payload,
                    params=params,
                )

        except httpx.TimeoutException as exc:
            logger.warning("Cashfree DigiLocker request timed out.")
            raise DigiLockerServiceError(
                504,
                "DigiLocker verification provider timed out. Please retry.",
            ) from exc

        except httpx.RequestError as exc:
            logger.warning(
                "Cashfree DigiLocker network request failed: %s",
                type(exc).__name__,
            )
            raise DigiLockerServiceError(
                502,
                "Unable to reach the verification provider.",
            ) from exc

        try:
            data = response.json()
        except ValueError:
            data = {}

        if not response.is_success:
            # Do not return provider response bodies directly because they
            # may contain sensitive identity information.
            logger.warning(
                "Cashfree DigiLocker returned HTTP %s.",
                response.status_code,
            )

            if response.status_code == 401:
                raise DigiLockerServiceError(
                    502,
                    "Cashfree authentication failed. Check server credentials.",
                )

            if response.status_code == 403:
                raise DigiLockerServiceError(
                    403,
                    "Cashfree denied the request. Check API permissions.",
                )

            if response.status_code == 429:
                raise DigiLockerServiceError(
                    429,
                    "Verification provider rate limit reached. Try again later.",
                )

            if response.status_code >= 500:
                raise DigiLockerServiceError(
                    502,
                    "Verification provider is temporarily unavailable.",
                )

            raise DigiLockerServiceError(
                400,
                "Verification provider rejected the request. Check the inputs.",
            )

        if not isinstance(data, dict):
            raise DigiLockerServiceError(
                502,
                "Verification provider returned an unexpected response.",
            )

        return data

    async def create_link(
        self,
        *,
        verification_id: str,
        redirect_url: str,
        user_flow: str = "signin",
    ) -> dict[str, Any]:
        if not re.fullmatch(r"[A-Za-z0-9._-]{1,50}", verification_id):
            raise DigiLockerServiceError(
                400,
                "Invalid verification ID.",
            )

        if user_flow not in {"signin", "signup"}:
            raise DigiLockerServiceError(
                400,
                "user_flow must be signin or signup.",
            )

        payload = {
            "verification_id": verification_id,
            "document_requested": ["AADHAAR"],
            "redirect_url": redirect_url,
            "user_flow": user_flow,
        }

        result = await self._request(
            "POST",
            "/digilocker",
            payload=payload,
        )

        # Return only the fields required by the frontend.
        return {
            "verification_id": result.get(
                "verification_id", verification_id
            ),
            "reference_id": result.get("reference_id"),
            "url": result.get("url"),
            "status": result.get("status"),
            "expires_in_seconds": 600,
        }

    async def get_status(
        self,
        *,
        verification_id: str,
    ) -> dict[str, Any]:
        if not re.fullmatch(r"[A-Za-z0-9._-]{1,50}", verification_id):
            raise DigiLockerServiceError(
                400,
                "Invalid verification ID.",
            )

        result = await self._request(
            "GET",
            "/digilocker",
            params={"verification_id": verification_id},
        )

        return result

    async def get_document(
        self,
        *,
        verification_id: str,
        document_type: str = "AADHAAR",
    ) -> dict[str, Any]:
        if not re.fullmatch(r"[A-Za-z0-9._-]{1,50}", verification_id):
            raise DigiLockerServiceError(
                400,
                "Invalid verification ID.",
            )

        document_type = document_type.upper()

        if document_type not in self.DOCUMENT_TYPES:
            raise DigiLockerServiceError(
                400,
                "Unsupported document type.",
            )

        # Call this only after the authenticated affiliate's verification
        # has been checked and confirmed successful.
        return await self._request(
            "GET",
            f"/digilocker/document/{document_type}",
            params={"verification_id": verification_id},
        )


digilocker_service = DigiLockerService()