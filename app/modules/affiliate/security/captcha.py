
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
    """Normalize a hostname for case-insensitive comparison."""
    if not hostname:
        return None

    return hostname.strip().rstrip(".").lower() or None


def _get_allowed_hostnames() -> set[str]:
    """
    Read explicitly allowed hostnames from application settings.

    Configure:
    CLOUDFLARE_TURNSTILE_ALLOWED_HOSTNAMES=
        energymaxgroup.in,www.energymaxgroup.in
    """
    raw_hostnames = getattr(
        settings,
        "cloudflare_turnstile_allowed_hostnames",
        "",
    )

    if not isinstance(raw_hostnames, str):
        return set()

    return {
        normalized
        for hostname in raw_hostnames.split(",")
        if (normalized := _normalize_hostname(hostname))
    }


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

    if not isinstance(secret, str) or not secret.strip():
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

    allowed_hostnames = _get_allowed_hostnames()

    if not allowed_hostnames:
        logger.error(
            "Cloudflare Turnstile allowed hostnames are not configured"
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Verification is temporarily unavailable.",
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

    payload: dict[str, str] = {
        "secret": secret.strip(),
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

    if (
        not actual_hostname
        or actual_hostname not in allowed_hostnames
    ):
        logger.warning(
            "Turnstile hostname mismatch: actual=%r allowed=%s",
            actual_hostname,
            sorted(allowed_hostnames),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CAPTCHA verification failed. Please try again.",
        )
