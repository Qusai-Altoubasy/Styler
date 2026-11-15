"""The manager's login, sessions and password."""

import asyncio
from collections import Counter

import pytest
from fastapi import FastAPI
from httpx import AsyncClient, Response
from sqlalchemy import func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import UnauthorizedError
from app.features.auth import service
from app.features.auth.cookies import SESSION_COOKIE
from app.features.auth.models import AdminSession
from app.features.settings.service import get_store_settings

PASSWORD = "first-password"
NEW_PASSWORD = "second-password"


@pytest.fixture(autouse=True)
async def manager_password(db_session: AsyncSession) -> None:
    await service.set_password(db_session, PASSWORD)


async def _login(client: AsyncClient, password: str = PASSWORD) -> Response:
    return await client.post("/api/admin/login", json={"password": password})


async def _is_logged_in(client: AsyncClient) -> bool:
    response = await client.get("/api/admin/session")
    assert response.status_code in (200, 401), response.text
    return response.status_code == 200


async def test_login_sets_a_strict_session_cookie(client: AsyncClient) -> None:
    response = await _login(client)

    assert response.status_code == 204
    cookie = response.headers["set-cookie"].lower()
    for flag in ("httponly", "secure", "samesite=strict", "path=/api/admin", "max-age=2592000"):
        assert flag in cookie
    assert await _is_logged_in(client)


async def test_wrong_password_is_refused(client: AsyncClient) -> None:
    response = await _login(client, "not-the-password")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_password"
    assert SESSION_COOKIE not in client.cookies


async def test_login_says_when_no_password_is_set_and_does_not_count_it(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    store = await get_store_settings(db_session)
    store.admin_password_hash = None
    await db_session.flush()

    for _ in range(6):
        response = await _login(client, "anything")
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "password_not_set"
    assert (await _login(client, "")).status_code == 422


async def test_unreadable_stored_hash_is_a_wrong_password_not_an_error(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    store = await get_store_settings(db_session)
    store.admin_password_hash = "not-an-argon2-hash"
    await db_session.flush()

    assert (await _login(client)).status_code == 401


async def test_admin_routes_need_a_session(client: AsyncClient) -> None:
    response = await client.get("/api/admin/session")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_authenticated"


async def test_a_forged_cookie_is_refused(client: AsyncClient) -> None:
    client.cookies.set(SESSION_COOKIE, "made-up-token")

    assert not await _is_logged_in(client)


async def test_expired_session_is_refused(client: AsyncClient, db_session: AsyncSession) -> None:
    await _login(client)
    await db_session.execute(
        update(AdminSession).values(expires_at=func.now() - text("interval '1 second'"))
    )

    assert not await _is_logged_in(client)


async def test_logout_ends_every_device(client: AsyncClient, other_device: AsyncClient) -> None:
    await _login(client)
    await _login(other_device)
    token = client.cookies[SESSION_COOKIE]

    response = await client.post("/api/admin/logout")

    assert response.status_code == 204
    assert SESSION_COOKIE not in client.cookies
    assert not await _is_logged_in(other_device)
    client.cookies.set(SESSION_COOKIE, token)
    assert not await _is_logged_in(client)


async def test_logout_with_an_ended_session_still_clears_the_cookie(
    client: AsyncClient, other_device: AsyncClient
) -> None:
    await _login(client)
    await _login(other_device)
    await client.post(
        "/api/admin/password", json={"current_password": PASSWORD, "new_password": NEW_PASSWORD}
    )

    response = await other_device.post("/api/admin/logout")

    assert response.status_code == 204
    assert SESSION_COOKIE not in other_device.cookies
    assert await _is_logged_in(client), "a dead cookie must not log the manager out"


async def test_logout_without_a_session_logs_nobody_out(
    client: AsyncClient, other_device: AsyncClient
) -> None:
    await _login(client)
    other_device.cookies.set(SESSION_COOKIE, "made-up-token")

    assert (await other_device.post("/api/admin/logout")).status_code == 204
    other_device.cookies.clear()
    assert (await other_device.post("/api/admin/logout")).status_code == 204

    assert await _is_logged_in(client)


async def test_expired_sessions_are_ended_at_the_next_login(
    client: AsyncClient, other_device: AsyncClient, db_session: AsyncSession
) -> None:
    await _login(other_device)
    await db_session.execute(
        update(AdminSession).values(expires_at=func.now() - text("interval '1 second'"))
    )

    await _login(client)

    live = await db_session.scalar(select(func.count(AdminSession.id)))
    assert live == 1


async def test_password_change_ends_every_session_and_renews_this_one(
    client: AsyncClient, other_device: AsyncClient
) -> None:
    await _login(client)
    await _login(other_device)
    old_token = client.cookies[SESSION_COOKIE]

    response = await client.post(
        "/api/admin/password",
        json={"current_password": PASSWORD, "new_password": NEW_PASSWORD},
    )

    assert response.status_code == 204
    assert not await _is_logged_in(other_device)
    assert await _is_logged_in(client)
    assert client.cookies[SESSION_COOKIE] != old_token
    other_device.cookies.set(SESSION_COOKIE, old_token)
    assert not await _is_logged_in(other_device)
    assert (await _login(other_device, PASSWORD)).status_code == 401
    assert (await _login(other_device, NEW_PASSWORD)).status_code == 204


async def test_password_change_needs_the_current_password(client: AsyncClient) -> None:
    await _login(client)

    response = await client.post(
        "/api/admin/password",
        json={"current_password": "wrong-password", "new_password": NEW_PASSWORD},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "wrong_current_password"
    assert await _is_logged_in(client)


async def test_new_password_must_be_long_enough(client: AsyncClient) -> None:
    await _login(client)

    response = await client.post(
        "/api/admin/password", json={"current_password": PASSWORD, "new_password": "short"}
    )

    assert response.status_code == 422


async def test_sixth_wrong_password_is_refused_even_when_correct(client: AsyncClient) -> None:
    for _ in range(5):
        assert (await _login(client, "wrong-password")).status_code == 401

    response = await _login(client)

    assert response.status_code == 429
    assert int(response.headers["Retry-After"]) > 0
    assert response.json()["error"]["code"] == "too_many_requests"


async def test_successful_logins_do_not_count(client: AsyncClient) -> None:
    for _ in range(4):
        await _login(client, "wrong-password")
    for _ in range(3):
        assert (await _login(client)).status_code == 204

    assert (await _login(client, "wrong-password")).status_code == 401
    assert (await _login(client, "wrong-password")).status_code == 429


async def test_parallel_wrong_passwords_cannot_slip_past_the_limit(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A slow wrong password, without the database: the test requests share one
    # connection, which cannot run queries in parallel.
    checked: list[str] = []

    async def slow_wrong_password(_session: object, password: str) -> str:
        checked.append(password)
        await asyncio.sleep(0.01)
        raise UnauthorizedError("invalid_password", "Wrong password")

    monkeypatch.setattr(service, "login", slow_wrong_password)

    responses = await asyncio.gather(*(_login(client, f"guess-{n}") for n in range(20)))

    assert Counter(response.status_code for response in responses) == {401: 5, 429: 15}
    assert len(checked) == 5, "every password beyond the limit must be refused unchecked"


async def test_wrong_current_passwords_count_toward_the_same_limit(client: AsyncClient) -> None:
    await _login(client)
    body = {"current_password": "wrong-password", "new_password": NEW_PASSWORD}
    for _ in range(5):
        await client.post("/api/admin/password", json=body)

    assert (await client.post("/api/admin/password", json=body)).status_code == 429


async def test_limits_follow_the_client_ip_header_when_configured(
    client: AsyncClient, test_app: FastAPI
) -> None:
    header = "CloudFront-Viewer-Address"
    behind_cdn = get_settings().model_copy(update={"client_ip_header": header})
    test_app.dependency_overrides[get_settings] = lambda: behind_cdn
    try:
        for _ in range(5):
            await client.post(
                "/api/admin/login",
                json={"password": "wrong-password"},
                headers={header: "198.51.100.10:1111"},
            )
        blocked = await client.post(
            "/api/admin/login", json={"password": PASSWORD}, headers={header: "198.51.100.10:2"}
        )
        other_customer = await client.post(
            "/api/admin/login", json={"password": PASSWORD}, headers={header: "203.0.113.7:3"}
        )
    finally:
        test_app.dependency_overrides.pop(get_settings, None)

    assert blocked.status_code == 429
    assert other_customer.status_code == 204
