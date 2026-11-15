"""The manager's login and sessions.

One manager, one password (an argon2 hash in the settings row), one session per
device. The cookie carries a random token; the database keeps only its SHA-256.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import ColumnElement, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, InvalidRequestError, UnauthorizedError
from app.core.security import hash_password, new_session_token, token_hash, verify_password
from app.features.auth.models import AdminSession
from app.features.settings import service as settings_service

SESSION_LIFETIME = timedelta(days=30)
"""Long, because the manager opens the dashboard from the phone's home screen."""


class WrongPasswordError(UnauthorizedError):
    def __init__(self) -> None:
        super().__init__("invalid_password", "Wrong password")


class WrongCurrentPasswordError(InvalidRequestError):
    """422, not 401: the manager is logged in, only the typed password is wrong."""

    def __init__(self) -> None:
        super().__init__("wrong_current_password", "The current password is wrong")


class PasswordNotSetError(ConflictError):
    """No password exists yet: the server command was never run (first deploy)."""

    def __init__(self) -> None:
        super().__init__(
            "password_not_set", "No password is set yet; run cli.set_password on the server"
        )


async def login(session: AsyncSession, password: str) -> str:
    """Open a session on this device and return its token."""
    stored_hash = await settings_service.get_admin_password_hash(session)
    if stored_hash is None:
        raise PasswordNotSetError()
    if not await verify_password(stored_hash, password):
        raise WrongPasswordError()
    token = await _open_session(session)
    await session.commit()
    return token


async def change_password(session: AsyncSession, current_password: str, new_password: str) -> str:
    """Set a new password, end every session, and return a fresh token for this device."""
    stored_hash = await settings_service.get_admin_password_hash(session)
    if not await verify_password(stored_hash, current_password):
        raise WrongCurrentPasswordError()
    await _replace_password(session, new_password)
    token = await _open_session(session)
    await session.commit()
    return token


async def set_password(session: AsyncSession, password: str) -> None:
    """Set the password without the old one (the server command), ending every session."""
    await _replace_password(session, password)
    await session.commit()


async def logout(session: AsyncSession, token: str | None) -> None:
    """End every session on every device, if `token` is a live session.

    Without a live session nothing happens: logging the manager out takes a session.
    """
    if token and await find_live_session(session, token):
        await _end_sessions(session)
        await session.commit()


async def find_live_session(session: AsyncSession, token: str) -> AdminSession | None:
    stmt = select(AdminSession).where(
        AdminSession.token_hash == token_hash(token), AdminSession.expires_at > func.now()
    )
    return await session.scalar(stmt)


async def _replace_password(session: AsyncSession, password: str) -> None:
    await settings_service.set_admin_password_hash(session, await hash_password(password))
    await _end_sessions(session)


async def _open_session(session: AsyncSession) -> str:
    await _end_sessions(session, AdminSession.expires_at <= func.now())
    token = new_session_token()
    session.add(
        AdminSession(token_hash=token_hash(token), expires_at=datetime.now(UTC) + SESSION_LIFETIME)
    )
    await session.flush()
    return token


async def _end_sessions(session: AsyncSession, *conditions: ColumnElement[bool]) -> None:
    """Soft-delete live sessions: all of them, or those matching `conditions`
    (e.g. the expired ones, ended at each login so they do not pile up as live rows)."""
    await session.execute(update(AdminSession).where(*conditions).values(deleted_at=func.now()))
