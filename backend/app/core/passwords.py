"""Argon2id password hashing."""

from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

_hasher = PasswordHasher()

MIN_PASSWORD_LEN = 8
MAX_PASSWORD_LEN = 128


def validate_password_plain(password: str) -> None:
    from fastapi import HTTPException

    if len(password) < MIN_PASSWORD_LEN or len(password) > MAX_PASSWORD_LEN:
        raise HTTPException(status_code=400, detail="PASSWORD_INVALID_LENGTH")


def hash_password(password: str) -> str:
    validate_password_plain(password)
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        return False
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False
