"""Test setup: a real PostgreSQL database built with `alembic upgrade head`.

The tests never touch the development database or bucket. Before anything from `app`
is imported, DATABASE_URL is replaced by TEST_DATABASE_URL, and that database is
dropped and rebuilt from the migrations once per test run; S3_BUCKET is replaced by
TEST_S3_BUCKET.
"""

import asyncio
import os
from collections.abc import AsyncIterator, Iterator
from typing import cast

import pytest

TEST_DATABASE_URL: str = os.environ.get("TEST_DATABASE_URL", "")
if not TEST_DATABASE_URL:
    raise RuntimeError("TEST_DATABASE_URL is not set (see deploy/.env.dev.example)")
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

# Images go to their own bucket too, emptied by the media tests (tests/media/conftest.py).
TEST_S3_BUCKET: str = os.environ.get("TEST_S3_BUCKET", "")
if not TEST_S3_BUCKET.endswith("-test"):
    raise RuntimeError("TEST_S3_BUCKET must be set and end in -test (see deploy/.env.dev.example)")
os.environ["S3_BUCKET"] = TEST_S3_BUCKET

import asyncpg  # noqa: E402
from alembic.config import Config  # noqa: E402
from botocore.exceptions import ClientError  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from mypy_boto3_s3.literals import BucketLocationConstraintType  # noqa: E402
from mypy_boto3_s3.type_defs import ObjectIdentifierTypeDef  # noqa: E402
from sqlalchemy.engine import make_url  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession  # noqa: E402

from alembic import command  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.core.db import engine, get_session  # noqa: E402
from app.core.rate_limit import reset_all_limiters  # noqa: E402
from app.core.storage import storage_client  # noqa: E402
from app.features.auth import service as auth_service  # noqa: E402
from app.main import app  # noqa: E402

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def alembic_config() -> Config:
    config = Config(os.path.join(BACKEND_DIR, "alembic.ini"))
    config.attributes["database_url"] = TEST_DATABASE_URL
    config.attributes["configure_logger"] = False
    return config


async def _recreate_test_database() -> None:
    url = make_url(TEST_DATABASE_URL)
    name = url.database
    if not name or not name.endswith("_test"):
        raise RuntimeError(f"Refusing to drop {name!r}: the test database name must end in _test")
    connection = await asyncpg.connect(
        host=url.host,
        port=url.port or 5432,
        user=url.username,
        password=url.password,
        database="postgres",
    )
    try:
        await connection.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
        await connection.execute(f'CREATE DATABASE "{name}"')
    finally:
        await connection.close()


@pytest.fixture(scope="session", autouse=True)
def database() -> None:
    """Build the test database from scratch, exactly as on a new server.

    It also goes down to an empty database and back up once, so every migration's
    downgrade (used in local development) is exercised too.
    """
    asyncio.run(_recreate_test_database())
    config = alembic_config()
    command.upgrade(config, "head")
    command.downgrade(config, "base")
    command.upgrade(config, "head")


@pytest.fixture
async def db_connection() -> AsyncIterator[AsyncConnection]:
    """One connection per test, inside a transaction that is rolled back afterwards."""
    async with engine.connect() as connection:
        transaction = await connection.begin()
        try:
            yield connection
        finally:
            await transaction.rollback()


def _session_on(connection: AsyncConnection) -> AsyncSession:
    # Commits become savepoints inside the test's transaction, so nothing is left behind.
    return AsyncSession(
        bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False
    )


@pytest.fixture
async def db_session(db_connection: AsyncConnection) -> AsyncIterator[AsyncSession]:
    """The test's own session, for adding rows and checking results."""
    session = _session_on(db_connection)
    try:
        yield session
    finally:
        await session.close()


@pytest.fixture(autouse=True)
def fresh_rate_limits() -> None:
    """Every test client shares one address; start each test with empty counters."""
    reset_all_limiters()


@pytest.fixture
def test_app(db_connection: AsyncConnection) -> Iterator[FastAPI]:
    """The app, on the test's connection.

    Every request gets a fresh session, like in production: it sees the rows the test
    flushed, but not the test's loaded objects, and work it does not commit is lost.
    Everything is rolled back with the test.
    """

    async def _request_session() -> AsyncIterator[AsyncSession]:
        session = _session_on(db_connection)
        try:
            yield session
        finally:
            await session.close()

    app.dependency_overrides[get_session] = _request_session
    try:
        yield app
    finally:
        app.dependency_overrides.pop(get_session, None)


def _http_client(asgi_app: FastAPI) -> AsyncClient:
    # HTTPS, so Secure cookies are sent back like in a browser.
    return AsyncClient(transport=ASGITransport(app=asgi_app), base_url="https://test")


@pytest.fixture
async def client(test_app: FastAPI) -> AsyncIterator[AsyncClient]:
    """An HTTP client with its own cookies, like one browser."""
    async with _http_client(test_app) as http:
        yield http


@pytest.fixture
async def other_device(test_app: FastAPI) -> AsyncIterator[AsyncClient]:
    """A second browser with separate cookies, e.g. the manager's laptop."""
    async with _http_client(test_app) as http:
        yield http


MANAGER_PASSWORD = "manager-test-password"


@pytest.fixture
async def admin_client(client: AsyncClient, db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    """The `client` browser, logged in as the manager (the password is set first)."""
    await auth_service.set_password(db_session, MANAGER_PASSWORD)
    response = await client.post("/api/admin/login", json={"password": MANAGER_PASSWORD})
    assert response.status_code == 204, response.text
    yield client


@pytest.fixture(scope="session")
def test_bucket() -> str:
    """The TEST_S3_BUCKET bucket in MinIO, created on first use."""
    settings = get_settings()
    assert settings.s3_bucket.endswith("-test")
    client = storage_client()
    try:
        client.head_bucket(Bucket=settings.s3_bucket)
    except ClientError:
        region = cast(BucketLocationConstraintType, settings.s3_region)
        client.create_bucket(
            Bucket=settings.s3_bucket, CreateBucketConfiguration={"LocationConstraint": region}
        )
    return settings.s3_bucket


@pytest.fixture
def empty_bucket(test_bucket: str) -> str:
    """The test bucket, emptied before the test. Request it in any test that stores images,
    so it never depends on what an earlier test or run left behind."""
    client = storage_client()
    for page in client.get_paginator("list_objects_v2").paginate(Bucket=test_bucket):
        keys: list[ObjectIdentifierTypeDef] = [
            {"Key": item["Key"]} for item in page.get("Contents", []) if "Key" in item
        ]
        if keys:
            client.delete_objects(Bucket=test_bucket, Delete={"Objects": keys})
    return test_bucket
