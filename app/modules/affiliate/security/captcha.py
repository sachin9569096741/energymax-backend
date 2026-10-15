import logging

import httpx
from fastapi import HTTPException, status

from app.core.config import settings

logger = logging.getLogger(__name__)

TURNSTILE_VERIFY_URL = (
    "https://challenges.cloudflare.com/turnstile/v0/siteverify"
)


def verify_captcha(
    token: str,
    remote_ip: str | None = None,
) -> None:
    """Verify a Cloudflare Turnstile token on the backend."""

    secret = getattr(
        settings, "cloudflare_turnstile_secret_key", ""
    )
    expected_hostname = getattr(
        settings, "cloudflare_turnstile_expected_hostname", ""
    )

    # Do not silently disable CAPTCHA when the secret is missing.
    if not secret:
        logger.error("Cloudflare Turnstile secret is not configured")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Login verification is temporarily unavailable.",
        )

    if not token or len(token) > 4096:
        raise HTTPException(
            status_code=400,
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
            timeout=5.0,
        )
        response.raise_for_status()
        result = response.json()

    except (httpx.HTTPError, ValueError):
        logger.warning(
            "Turnstile verification service unavailable",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="CAPTCHA verification is temporarily unavailable.",
        )

    if result.get("success") is not True:
        raise HTTPException(
            status_code=400,
            detail="CAPTCHA verification failed. Please try again.",
        )

    if (
        expected_hostname
        and result.get("hostname") != expected_hostname
    ):
        logger.warning("Turnstile hostname mismatch")
        raise HTTPException(
            status_code=400,
            detail="CAPTCHA verification failed. Please try again.",
        )