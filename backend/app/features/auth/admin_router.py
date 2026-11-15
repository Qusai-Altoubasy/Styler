"""`/api/admin` auth endpoints. Login and logout are the only admin endpoints open without
a session."""

from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.client_ip import ClientKey
from app.core.db import get_session
from app.core.rate_limit import RateLimiter
from app.features.auth import service
from app.features.auth.cookies import clear_session_cookie, set_session_cookie
from app.features.auth.dependencies import CurrentSession, SessionToken, require_admin
from app.features.auth.schemas import LoginIn, PasswordChangeIn, SessionOut

open_router = APIRouter(tags=["auth"])
router = APIRouter(tags=["auth"], dependencies=[Depends(require_admin)])

Session = Annotated[AsyncSession, Depends(get_session)]

failed_password_attempts = RateLimiter(limit=5, window=timedelta(minutes=15))
"""Wrong passwords per IP, at login and when changing the password."""


@open_router.post("/login", status_code=status.HTTP_204_NO_CONTENT)
async def login(session: Session, client: ClientKey, data: LoginIn, response: Response) -> None:
    with failed_password_attempts.counting_only(client, failure=service.WrongPasswordError):
        token = await service.login(session, data.password)
    set_session_cookie(response, token)


@open_router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(session: Session, response: Response, token: SessionToken = None) -> None:
    """Logs out every device, this one included (also what to press for a lost phone).

    Open, so a device whose session already ended can still clear its cookie; the
    sessions are only ended when the cookie belongs to a live one.
    """
    await service.logout(session, token)
    clear_session_cookie(response)


@router.get("/session")
async def get_session_info(current: CurrentSession) -> SessionOut:
    """Whether the dashboard is logged in (200) or must show the login page (401)."""
    return SessionOut(expires_at=current.expires_at)


@router.post("/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    session: Session, client: ClientKey, data: PasswordChangeIn, response: Response
) -> None:
    """Every other device is logged out; this one gets a fresh session."""
    with failed_password_attempts.counting_only(client, failure=service.WrongCurrentPasswordError):
        token = await service.change_password(session, data.current_password, data.new_password)
    set_session_cookie(response, token)
