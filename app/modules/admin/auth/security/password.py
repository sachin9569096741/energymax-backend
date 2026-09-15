from argon2 import PasswordHasher
from argon2.exceptions import (
    InvalidHash,
    VerificationError,
    VerifyMismatchError,
)


_password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    """
    Hash a plaintext password using Argon2.
    """
    return _password_hasher.hash(password)


def verify_password(
    password: str,
    password_hash: str,
) -> bool:
    """
    Verify a plaintext password against an Argon2 hash.
    """

    try:
        return _password_hasher.verify(
            password_hash,
            password,
        )

    except (
        VerifyMismatchError,
        VerificationError,
        InvalidHash,
    ):
        return False


def needs_rehash(password_hash: str) -> bool:
    """
    Check whether the stored Argon2 hash should be upgraded.
    """
    return _password_hasher.check_needs_rehash(
        password_hash
    )