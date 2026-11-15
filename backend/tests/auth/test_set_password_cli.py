"""The server command that sets the password when the manager forgets it."""

import getpass
from collections.abc import Iterator

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.features.auth import service
from app.features.auth.models import AdminSession
from app.features.settings.service import get_admin_password_hash
from cli import set_password


def _typed(monkeypatch: pytest.MonkeyPatch, *answers: str) -> None:
    replies: Iterator[str] = iter(answers)
    monkeypatch.setattr(getpass, "getpass", lambda _prompt: next(replies))


def test_password_typed_twice_is_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    _typed(monkeypatch, "a long password", "a long password")

    assert set_password._ask_password() == "a long password"


@pytest.mark.parametrize("answers", [("a long password", "a typo password"), ("short", "short")])
def test_mismatched_or_short_password_changes_nothing(
    monkeypatch: pytest.MonkeyPatch, answers: tuple[str, str]
) -> None:
    _typed(monkeypatch, *answers)

    with pytest.raises(SystemExit):
        set_password._ask_password()


async def test_setting_the_password_logs_every_device_out(db_session: AsyncSession) -> None:
    await service.set_password(db_session, "first password")
    await service.login(db_session, "first password")
    await service.login(db_session, "first password")

    await service.set_password(db_session, "second password")

    live = await db_session.scalar(select(func.count(AdminSession.id)))
    assert live == 0
    stored = await get_admin_password_hash(db_session)
    assert await verify_password(stored, "second password")
