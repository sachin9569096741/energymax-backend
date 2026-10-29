import logging
import re
from typing import Any

import httpx

from app.core.config import settings


logger = logging.getLogger(__name__)


class KYCServiceError(Exception):
    """Expected error raised by the Cashfree Secure ID integration."""

    def __init__(
        self,
        message: str,
        status_code: int = 400,
        provider_status_code: int | None = None,
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.provider_status_code = provider_status_code
        super().__init__(message)


class KYCService:
    """
    Cashfree Secure ID integration for EnergyMax affiliate KYC.

    Supported operations:
        1. PAN verification
        2. Aadhaar OTP generation
        3. Aadhaar OTP verification

    This service does not persist KYC data.
    The API/database layer must bind Aadhaar OTP references
    to the authenticated affiliate.
    """

    TIMEOUT = 20.0

    PAN_PATTERN = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")
    AADHAAR_PATTERN = re.compile(r"^[0-9]{12}$")
    OTP_PATTERN = re.compile(r"^[0-9]{6}$")

    def __init__(self) -> None:
        self.client_id = str(
            getattr(
                settings,
                "cashfree_verification_client_id",
                "",
            )
            or ""
        ).strip()

        self.client_secret = str(
            getattr(
                settings,
                "cashfree_verification_client_secret",
                "",
            )
            or ""
        ).strip()

        environment = str(
            getattr(
                settings,
                "cashfree_verification_environment",
                "sandbox",
            )
            or "sandbox"
        ).strip().lower()

        if environment in {"sandbox", "test"}:
            self.environment = "sandbox"
            self.base_url = (
                "https://sandbox.cashfree.com/verification"
            )

        elif environment in {"production", "prod"}:
            self.environment = "production"
            self.base_url = (
                "https://api.cashfree.com/verification"
            )

        else:
            raise KYCServiceError(
                "Invalid Cashfree verification environment.",
                status_code=500,
            )

    # ---------------------------------------------------------
    # HEADERS
    # ---------------------------------------------------------

    def _get_headers(self) -> dict[str, str]:
        """Build Cashfree Secure ID request headers."""

        if not self.client_id or not self.client_secret:
            raise KYCServiceError(
                "Cashfree Secure ID credentials are not configured.",
                status_code=500,
            )

        return {
            "x-client-id": self.client_id,
            "x-client-secret": self.client_secret,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    # ---------------------------------------------------------
    # PROVIDER ERROR HANDLING
    # ---------------------------------------------------------

    @staticmethod
    def _safe_provider_message(
        response: httpx.Response,
    ) -> str:
        """
        Extract a short provider message for server-side diagnostics.

        Never log request payloads, credentials, PAN, Aadhaar,
        OTP, or the complete provider response.
        """

        try:
            body = response.json()

        except ValueError:
            return "Cashfree returned a non-JSON error response."

        if not isinstance(body, dict):
            return "Cashfree returned an unexpected error response."

        for key in (
            "message",
            "error_description",
            "error",
            "type",
        ):
            value = body.get(key)

            if isinstance(value, str) and value.strip():
                return value.strip().replace("\n", " ")[:200]

        return "Cashfree returned an unsuccessful response."

    # ---------------------------------------------------------
    # COMMON POST REQUEST
    # ---------------------------------------------------------

    async def _post(
        self,
        endpoint: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Send a JSON request to Cashfree Secure ID."""

        if not endpoint.startswith("/") or ".." in endpoint:
            raise KYCServiceError(
                "Invalid verification endpoint.",
                status_code=500,
            )

        headers = self._get_headers()
        url = f"{self.base_url}{endpoint}"

        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(self.TIMEOUT),
                follow_redirects=False,
            ) as client:

                response = await client.post(
                    url,
                    headers=headers,
                    json=payload,
                )

        except httpx.TimeoutException as exc:
            logger.warning(
                "Cashfree KYC request timed out: endpoint=%s",
                endpoint,
            )

            raise KYCServiceError(
                "Verification provider timed out. Please try again.",
                status_code=504,
            ) from exc

        except httpx.RequestError as exc:
            # Avoid logging the exception text because it can
            # contain request details.
            logger.warning(
                "Cashfree KYC connection failed: "
                "endpoint=%s error_type=%s",
                endpoint,
                type(exc).__name__,
            )

            raise KYCServiceError(
                "Unable to connect to the verification provider.",
                status_code=502,
            ) from exc

        # Handle unsuccessful provider responses.
        if not response.is_success:

            provider_message = self._safe_provider_message(
                response
            )

            logger.warning(
                "Cashfree KYC request failed: "
                "endpoint=%s http_status=%s provider_message=%s",
                endpoint,
                response.status_code,
                provider_message,
            )

            if response.status_code == 401:
                message = (
                    "Cashfree authentication failed. Check the "
                    "Secure ID credentials and environment."
                )
                api_status = 502

            elif response.status_code == 403:
                message = (
                    "Cashfree denied the request. Check Secure ID "
                    "product access and IP restrictions."
                )
                api_status = 502

            elif response.status_code == 422:
                message = (
                    "Cashfree rejected the request parameters. "
                    "Check the endpoint and request schema."
                )
                api_status = 502

            elif response.status_code == 429:
                message = (
                    "Cashfree rate limit reached. "
                    "Please try again later."
                )
                api_status = 503

            elif response.status_code >= 500:
                message = (
                    "Cashfree verification service encountered "
                    "an error."
                )
                api_status = 502

            else:
                message = (
                    "Cashfree rejected the verification request."
                )
                api_status = 502

            raise KYCServiceError(
                message,
                status_code=api_status,
                provider_status_code=response.status_code,
            )

        # Parse successful response.
        try:
            result = response.json()

        except ValueError as exc:
            logger.warning(
                "Cashfree KYC returned invalid JSON: "
                "endpoint=%s status=%s",
                endpoint,
                response.status_code,
            )

            raise KYCServiceError(
                "Cashfree returned an invalid response.",
                status_code=502,
                provider_status_code=response.status_code,
            ) from exc

        if not isinstance(result, dict):
            raise KYCServiceError(
                "Cashfree returned an unexpected response format.",
                status_code=502,
                provider_status_code=response.status_code,
            )

        return result

    # ---------------------------------------------------------
    # MASKING HELPERS
    # ---------------------------------------------------------

    @staticmethod
    def _mask_pan(pan: str) -> str:
        """Mask PAN before returning it to the client."""

        return f"{pan[:2]}******{pan[-2:]}"

    @staticmethod
    def _mask_aadhaar(aadhaar: str) -> str:
        """Show only the last four Aadhaar digits."""

        return f"XXXX-XXXX-{aadhaar[-4:]}"

    # ---------------------------------------------------------
    # PAN VERIFICATION
    # ---------------------------------------------------------

    async def verify_pan(
        self,
        pan: str,
        name: str | None = None,
    ) -> dict[str, Any]:
        """Verify PAN through Cashfree Secure ID."""

        if not isinstance(pan, str):
            raise KYCServiceError(
                "PAN must be a string."
            )

        pan = pan.strip().upper()

        if not self.PAN_PATTERN.fullmatch(pan):
            raise KYCServiceError(
                "Invalid PAN format. Expected 10 characters."
            )

        payload: dict[str, Any] = {
            "pan": pan,
        }

        if name is not None:
            if not isinstance(name, str) or not name.strip():
                raise KYCServiceError(
                    "Name cannot be empty when provided."
                )

            payload["name"] = name.strip()

        result = await self._post(
            "/pan",
            payload,
        )

        # A successful HTTP response does not automatically
        # establish that the PAN itself is valid.
        #
        # Confirm these response fields against the exact
        # Cashfree Secure ID product enabled for your account.
        provider_status = str(
            result.get("status") or ""
        ).strip().upper()

        pan_status = str(
            result.get("pan_status") or ""
        ).strip().upper()

        valid_value = result.get("valid")

        verified = (
            valid_value is True
            or pan_status in {"VALID", "ACTIVE"}
        )

        if provider_status in {
            "ERROR",
            "FAILED",
            "FAILURE",
        }:
            verified = False

        verification_id = (
            result.get("verification_id")
            or result.get("reference_id")
            or result.get("ref_id")
        )

        return {
            "document_type": "PAN",
            "masked_pan": self._mask_pan(pan),
            "verified": verified,
            "provider_status": provider_status or None,
            "verification_id": (
                str(verification_id)
                if verification_id
                else None
            ),
            "message": (
                "PAN verified successfully."
                if verified
                else "PAN verification was not confirmed "
                "by the provider."
            ),
        }

    # ---------------------------------------------------------
    # AADHAAR OTP GENERATION
    # ---------------------------------------------------------

    async def send_aadhaar_otp(
        self,
        aadhaar_number: str,
    ) -> dict[str, Any]:
        """Initiate Aadhaar OTP verification."""

        if not isinstance(aadhaar_number, str):
            raise KYCServiceError(
                "Aadhaar number must be a string."
            )

        aadhaar_number = aadhaar_number.strip()

        if not self.AADHAAR_PATTERN.fullmatch(
            aadhaar_number
        ):
            raise KYCServiceError(
                "Aadhaar must contain exactly 12 digits."
            )

        result = await self._post(
            "/offline-aadhaar/otp",
            {
                "aadhaar_number": aadhaar_number,
            },
        )

        reference_id = (
            result.get("ref_id")
            or result.get("reference_id")
        )

        if not reference_id:
            logger.warning(
                "Cashfree Aadhaar OTP response "
                "was missing a reference ID."
            )

            raise KYCServiceError(
                "OTP initiation could not be confirmed. "
                "Please try again.",
                status_code=502,
            )

        return {
            "document_type": "AADHAAR",
            "masked_aadhaar": self._mask_aadhaar(
                aadhaar_number
            ),
            "otp_sent": True,
            "reference_id": str(reference_id),
            "message": "Aadhaar OTP initiation successful.",
        }

    # ---------------------------------------------------------
    # AADHAAR OTP VERIFICATION
    # ---------------------------------------------------------

    async def verify_aadhaar_otp(
        self,
        reference_id: str,
        otp: str,
    ) -> dict[str, Any]:
        """Verify Aadhaar OTP for a previously initiated request."""

        if not isinstance(reference_id, str):
            raise KYCServiceError(
                "Invalid Aadhaar verification reference."
            )

        reference_id = reference_id.strip()

        if not reference_id or len(reference_id) > 200:
            raise KYCServiceError(
                "Invalid Aadhaar verification reference."
            )

        if not isinstance(otp, str):
            raise KYCServiceError(
                "OTP must be a string."
            )

        otp = otp.strip()

        if not self.OTP_PATTERN.fullmatch(otp):
            raise KYCServiceError(
                "OTP must contain exactly 6 digits."
            )

        result = await self._post(
            "/offline-aadhaar/verify",
            {
                "ref_id": reference_id,
                "otp": otp,
            },
        )

        provider_status = str(
            result.get("status") or ""
        ).strip().upper()

        verified = provider_status in {
            "SUCCESS",
            "VALID",
            "VERIFIED",
        }

        return {
            "document_type": "AADHAAR",
            "verified": verified,
            "provider_status": provider_status or None,
            "reference_id": reference_id,
            "message": (
                "Aadhaar verified successfully."
                if verified
                else "Aadhaar verification was not confirmed "
                "by the provider."
            ),
        }


# Shared service instance.
kyc_service = KYCService()