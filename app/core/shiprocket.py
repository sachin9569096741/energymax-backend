
import logging
import threading
import time
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

TOKEN_REFRESH_BUFFER_SECONDS = 300
DEFAULT_TOKEN_TTL_SECONDS = 9 * 24 * 60 * 60


class ShiprocketError(Exception):
    """Raised when a Shiprocket API operation fails."""


class ShiprocketClient:
    def __init__(self) -> None:
        self.base_url = settings.shiprocket_base_url.rstrip("/")
        self.email = settings.shiprocket_api_email
        self.password = settings.shiprocket_api_password

        self._token: str | None = None
        self._token_expires_at = 0.0
        self._lock = threading.Lock()

        if not self.email or not self.password:
            raise ShiprocketError(
                "Shiprocket API credentials are not configured."
            )

    def _login(self) -> str:
        """Authenticate and obtain a Shiprocket bearer token."""
        url = f"{self.base_url}/auth/login"

        try:
            response = httpx.post(
                url,
                json={
                    "email": self.email,
                    "password": self.password,
                },
                timeout=15.0,
            )
            response.raise_for_status()
            data = response.json()

        except httpx.TimeoutException as exc:
            raise ShiprocketError(
                "Shiprocket authentication timed out."
            ) from exc

        except httpx.HTTPStatusError as exc:
            logger.warning(
                "Shiprocket authentication returned HTTP %s",
                exc.response.status_code,
            )
            raise ShiprocketError(
                "Shiprocket authentication failed. "
                "Check the API credentials and account access."
            ) from None

        except (httpx.HTTPError, ValueError) as exc:
            raise ShiprocketError(
                "Could not communicate with Shiprocket authentication."
            ) from exc

        token = data.get("token") if isinstance(data, dict) else None

        if not isinstance(token, str) or not token:
            raise ShiprocketError(
                "Shiprocket did not return a valid bearer token."
            )

        # Shiprocket tokens commonly expire after 10 days.
        # Cache conservatively; a 401 response triggers a fresh login.
        self._token = token
        self._token_expires_at = (
            time.monotonic() + DEFAULT_TOKEN_TTL_SECONDS
        )

        logger.info("Shiprocket authentication succeeded")
        return token

    def _get_token(self, force_refresh: bool = False) -> str:
        """Return a cached token or authenticate again."""
        with self._lock:
            token_is_valid = (
                self._token is not None
                and time.monotonic()
                < self._token_expires_at
                - TOKEN_REFRESH_BUFFER_SECONDS
            )

            if not force_refresh and token_is_valid:
                return self._token

            return self._login()

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> Any:
        """Make an authenticated request to Shiprocket."""
        if not path or path.startswith(("http://", "https://")):
            raise ValueError("Provide a relative Shiprocket API path.")

        url = f"{self.base_url}/{path.lstrip('/')}"
        token = self._get_token()

        for attempt in range(2):
            try:
                response = httpx.request(
                    method=method.upper(),
                    url=url,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/json",
                    },
                    params=params,
                    json=json,
                    timeout=20.0,
                )

                if response.status_code == 401 and attempt == 0:
                    token = self._get_token(force_refresh=True)
                    continue

                response.raise_for_status()

                if not response.content:
                    return None

                return response.json()

            except httpx.TimeoutException as exc:
                raise ShiprocketError(
                    "Shiprocket API request timed out."
                ) from exc

            except httpx.HTTPStatusError as exc:
                logger.warning(
                    "Shiprocket API returned HTTP %s for %s",
                    exc.response.status_code,
                    path,
                )
                raise ShiprocketError(
                    f"Shiprocket API request failed "
                    f"(HTTP {exc.response.status_code})."
                ) from None

            except (httpx.HTTPError, ValueError) as exc:
                raise ShiprocketError(
                    "Could not process the Shiprocket API response."
                ) from exc

        raise ShiprocketError(
            "Shiprocket authentication failed after token refresh."
        )
