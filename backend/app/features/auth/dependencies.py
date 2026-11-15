from typing import Annotated

from fastapi import Cookie, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.errors import UnauthorizedError
from app.features.auth import service
from app.features.auth.cookies import SESSION_COOKIE
from app.features.auth.models import AdminSession

SessionToken = Annotated[str | None, Cookie(alias=SESSION_COOKIE)]
"""The session cookie's token, if the browser sent one."""


async def require_admin(
    session: Annotated[AsyncSession, Depends(get_session)], token: SessionToken = None
) -> AdminSession:
    """The manager's live session, or 401. Protects every `/api/admin` router."""
    admin_session = await service.find_live_session(session, token) if token else None
    if admin_session is None:
        raise UnauthorizedError("not_authenticated", "Log in first")
    return admin_session


CurrentSession = Annotated[AdminSession, Depends(require_admin)]
