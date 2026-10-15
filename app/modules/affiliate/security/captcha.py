
import logging

import httpx
from fastapi import HTTPException, status

from app.core.config import settings

logger = logging.getLogger(__name__)

TURNSTILE_VERIFY_URL = (
    "https://challenges.cloudflare.com/turnstile/v0/siteverify"
)
TURNSTILE_TIMEOUT_SECONDS = 5.0
MAX_TOKEN_LENGTH = 4096


def _normalize_hostname(hostname: str | None) -> str | None:
    """Normalize a hostname for safe, case-insensitive comparison."""
    if not hostname:
        return None

    return hostname.strip().rstrip(".").lower()


def verify_captcha(
    token: str | None,
    remote_ip: str | None = None,
) -> None:
    """Verify a Cloudflare Turnstile token on the backend."""

    secret = getattr(
        settings,
        "cloudflare_turnstile_secret_key",
        "",
    )

    expected_hostname = _normalize_hostname(
        getattr(
            settings,
            "cloudflare_turnstile_expected_hostname",
            "",
        )
    )

    # Fail closed if server configuration is incomplete.
    if not secret:
        logger.error(
            "Cloudflare Turnstile secret is not configured"
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Verification is temporarily unavailable. "
                "Please try again later."
            ),
        )

    if not isinstance(token, str) or not token.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please complete the CAPTCHA and try again.",
        )

    token = token.strip()

    if len(token) > MAX_TOKEN_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CAPTCHA verification failed. Please try again.",
        )

    payload = {
        "secret": secret,
        "response": token,
    }

    if remote_ip:
        payload["remoteip"] = remote_ip

    try:
        response = httpx.post(
            TURNSTILE_VERIFY_URL,
            data=payload,
            timeout=TURNSTILE_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        result = response.json()

        if not isinstance(result, dict):
            raise ValueError(
                "Unexpected Turnstile response format"
            )

    except (httpx.HTTPError, ValueError):
        logger.warning(
            "Turnstile verification service unavailable",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "CAPTCHA verification is temporarily unavailable. "
                "Please try again."
            ),
        ) from None

    # Cloudflare explicitly indicates whether verification succeeded.
    if result.get("success") is not True:
        logger.warning(
            "Turnstile verification failed: error_codes=%s",
            result.get("error-codes"),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CAPTCHA verification failed. Please try again.",
        )

    actual_hostname = _normalize_hostname(
        result.get("hostname")
    )

    # Require an explicitly configured hostname and a hostname
    # returned by Cloudflare. Never silently skip this security check.
    if not expected_hostname:
        logger.error(
            "Cloudflare Turnstile expected hostname is not configured"
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Verification is temporarily unavailable.",
        )

    if not actual_hostname or actual_hostname != expected_hostname:
        logger.warning(
            "Turnstile hostname mismatch: expected=%r actual=%r",
            expected_hostname,
            actual_hostname,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CAPTCHA verification failed. Please try again.",
        )
