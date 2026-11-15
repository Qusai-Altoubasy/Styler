"""Password hashing (argon2) and session tokens.

argon2 is slow and memory-hungry on purpose (64 MiB per hash with the library's
defaults). It runs in a worker thread so the event loop keeps serving, and only one
hash runs at a time, so a burst of login attempts cannot exhaust the 1 GB server.
"""

import asyncio
import hashlib
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from starlette.concurrency import run_in_threadpool

_hasher = PasswordHasher()
_one_hash_at_a_time = asyncio.Semaphore(1)


async def hash_password(password: str) -> str:
    async with _one_hash_at_a_time:
        return await run_in_threadpool(_hasher.hash, password)


async def verify_password(stored_hash: str | None, password: str) -> bool:
    """False for a wrong password, and also when no password is set or the stored
    hash is unreadable: the caller only ever sees "does not match"."""
    if stored_hash is None:
        return False
    async with _one_hash_at_a_time:
        try:
            return await run_in_threadpool(_hasher.verify, stored_hash, password)
        except VerificationError, InvalidHashError:
            return False


def new_session_token() -> str:
    """A random token for the session cookie (256 bits)."""
    return secrets.token_urlsafe(32)


def token_hash(token: str) -> str:
    """What the database stores instead of the token: its SHA-256, in hex."""
    return hashlib.sha256(token.encode()).hexdigest()
