"""Password hashing and opaque token primitives."""

import hashlib
import hmac
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

# argon2-cffi defaults are Argon2id with the RFC 9106 low-memory profile
# (t=3, m=64 MiB, p=4). Pinned explicitly so a library upgrade cannot
# silently weaken them; check_needs_rehash() upgrades old hashes on login.
_hasher = PasswordHasher(time_cost=3, memory_cost=64 * 1024, parallelism=4)

# Verified against when the account does not exist, so a failed login takes
# the same time whether or not the email is registered.
_DUMMY_HASH = _hasher.hash(secrets.token_urlsafe(16))


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str | None, password: str) -> bool:
    try:
        return _hasher.verify(password_hash or _DUMMY_HASH, password) and password_hash is not None
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def password_needs_rehash(password_hash: str) -> bool:
    return _hasher.check_needs_rehash(password_hash)


def generate_token() -> str:
    """256-bit URL-safe random token."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> bytes:
    """Session tokens are high-entropy, so a fast hash is sufficient at rest."""
    return hashlib.sha256(token.encode("utf-8")).digest()


def tokens_match(expected: str, provided: str) -> bool:
    return hmac.compare_digest(expected.encode("utf-8"), provided.encode("utf-8"))
