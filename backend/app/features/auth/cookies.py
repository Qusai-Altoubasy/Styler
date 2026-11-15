"""The manager's session cookie.

HttpOnly (scripts cannot read it), Secure (HTTPS only), SameSite=Strict (never sent
from another site), and limited to `/api/admin` on the admin domain, so it never
travels with storefront requests.
"""

from fastapi import Response

from app.features.auth.service import SESSION_LIFETIME

SESSION_COOKIE = "styler_admin_session"
_PATH = "/api/admin"


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=int(SESSION_LIFETIME.total_seconds()),
        path=_PATH,
        secure=True,
        httponly=True,
        samesite="strict",
    )


def clear_session_cookie(response: Response) -> None:
    """Same name, path and flags as when it was set, or browsers keep the old one."""
    response.delete_cookie(
        SESSION_COOKIE, path=_PATH, secure=True, httponly=True, samesite="strict"
    )
