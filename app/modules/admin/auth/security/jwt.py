from datetime import datetime, timedelta, timezone

import jwt
from jwt import InvalidTokenError

from app.core.config import settings


class JWTError(Exception):
    """Raised when a JWT is invalid or cannot be processed."""


def create_access_token(
    *,
    user_id: int,
    public_id: str,
    username: str,
) -> str:
    """
    Create an access token for an authenticated admin user.
    """

    now = datetime.now(timezone.utc)

    expires_at = (
        now
        + timedelta(
            minutes=settings.jwt_access_token_expire_minutes
        )
    )

    payload = {
        "sub": str(user_id),
        "public_id": public_id,
        "username": username,
        "type": "access",
        "iat": now,
        "exp": expires_at,
    }

    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> dict:
    """
    Decode and validate an admin access token.
    """

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )

    except InvalidTokenError as exc:
        raise JWTError(
            "Invalid or expired access token."
        ) from exc

    if payload.get("type") != "access":
        raise JWTError(
            "Invalid token type."
        )

    if not payload.get("sub"):
        raise JWTError(
            "Token subject is missing."
        )

    return payload


def create_refresh_token(
    *,
    user_id: int,
    public_id: str,
    session_id: str,
) -> str:
    """
    Create a refresh token tied to an admin session.
    """

    now = datetime.now(timezone.utc)

    expires_at = (
        now
        + timedelta(
            days=settings.jwt_refresh_token_expire_days
        )
    )

    payload = {
        "sub": str(user_id),
        "public_id": public_id,
        "session_id": session_id,
        "type": "refresh",
        "iat": now,
        "exp": expires_at,
    }

    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def decode_refresh_token(token: str) -> dict:
    """
    Decode and validate an admin refresh token.
    """

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )

    except InvalidTokenError as exc:
        raise JWTError(
            "Invalid or expired refresh token."
        ) from exc

    if payload.get("type") != "refresh":
        raise JWTError(
            "Invalid token type."
        )

    if not payload.get("sub"):
        raise JWTError(
            "Token subject is missing."
        )

    if not payload.get("session_id"):
        raise JWTError(
            "Session ID is missing."
        )

    return payload