"""Password hashes: Argon2id, with the library's defaults (plan section 9.2)."""

from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

__all__ = ["MIN_LENGTH", "check_new", "hash_password", "needs_rehash", "verify"]

#: The shortest password accepted. A home network app; production work may ask for more.
MIN_LENGTH = 8

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify(password_hash: str | None, password: str) -> bool:
    if not password_hash:
        return False
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    return _hasher.check_needs_rehash(password_hash)


def check_new(password: str) -> None:
    """Raise ``ValueError`` with the reason when a new password is refused."""
    if len(password) < MIN_LENGTH:
        raise ValueError(f"A password needs at least {MIN_LENGTH} characters")
