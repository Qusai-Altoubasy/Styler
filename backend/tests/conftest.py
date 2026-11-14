"""Test setup: a real PostgreSQL database built with `alembic upgrade head`.

The tests never touch the development database. Before anything from `app` is
imported, DATABASE_URL is replaced by TEST_DATABASE_URL, and that database is
dropped and rebuilt from the migrations once per test run.
"""

import asyncio
import os
from collections.abc import AsyncIterator

import pytest

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
if not TEST_DATABASE_URL:
    raise RuntimeError("TEST_DATABASE_URL is not set (see deploy/.env.dev.example)")
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

import asyncpg  # noqa: E402
from alembic.config import Config  # noqa: E402
from sqlalchemy.engine import make_url  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from alembic import command  # noqa: E402
from app.core.db import engine  # noqa: E402

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
async def db_session() -> AsyncIterator[AsyncSession]:
    """A session inside a transaction that is rolled back after the test.

    Commits inside the test become savepoints, so nothing is left behind.
    """
    async with engine.connect() as connection:
        transaction = await connection.begin()
        session = AsyncSession(
            bind=connection,
            join_transaction_mode="create_savepoint",
            expire_on_commit=False,
        )
        try:
            yield session
        finally:
            await session.close()
            await transaction.rollback()
