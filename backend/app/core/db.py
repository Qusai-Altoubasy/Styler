"""Database engine, sessions, and the declarative base shared by every model.

- `Base` carries a fixed constraint naming convention, so every index and constraint
  has a predictable name from the first migration on.
- `TimestampMixin` adds `created_at` and `updated_at`.
- `SoftDeleteMixin` adds `deleted_at`. Every ORM SELECT, UPDATE and DELETE skips
  soft-deleted rows automatically; pass `execution_options(include_deleted=True)` to
  see them. Delete with `soft_delete()`, which also drops the row from the session,
  so a later `session.get()` cannot return it from memory.
"""

from collections.abc import AsyncIterator
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, MetaData, event, func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    ORMExecuteState,
    Session,
    mapped_column,
    with_loader_criteria,
)

from app.core.config import get_settings

NAMING_CONVENTION = {
    "pk": "pk_%(table_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
}

INCLUDE_DELETED = "include_deleted"
"""Execution option that turns off the soft-delete filter for one query."""

SOFT_DELETE_FILTER = "deleted_at IS NULL"
"""WHERE clause for partial unique indexes: uniqueness among live rows only."""


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
    # Fetch database-generated values (updated_at, deleted_at = now()) with RETURNING
    # on UPDATE too, not only on INSERT. Without it they are expired after a flush and
    # reading them in async code raises MissingGreenlet.
    __mapper_args__ = {"eager_defaults": True}  # noqa: RUF012


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class SoftDeleteMixin:
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


def str_enum[E: StrEnum](enum_cls: type[E], name: str) -> Enum:
    """A StrEnum stored as VARCHAR with a CHECK constraint, not a PostgreSQL ENUM type.

    Adding a value then only means replacing a CHECK constraint in a migration,
    instead of `ALTER TYPE`, which Alembic does not detect.
    """
    return Enum(
        enum_cls,
        name=name,
        native_enum=False,
        create_constraint=True,
        length=max(len(member.value) for member in enum_cls),
        values_callable=lambda members: [member.value for member in members],
    )


async def soft_delete(session: AsyncSession, instance: SoftDeleteMixin) -> None:
    """Mark a row deleted, and forget it in this session.

    After this, queries and `session.get()` behave as if the row were gone.
    """
    instance.deleted_at = func.now()
    await session.flush()
    # A SQL expression is not fetched back by the flush; load the stored time.
    await session.refresh(instance, ["deleted_at"])
    session.expunge(instance)


@event.listens_for(Session, "do_orm_execute")
def _exclude_soft_deleted(state: ORMExecuteState) -> None:
    if (
        (state.is_select or state.is_update or state.is_delete)
        and not state.is_column_load
        and not state.is_relationship_load
        and not state.execution_options.get(INCLUDE_DELETED, False)
    ):
        state.statement = state.statement.options(
            with_loader_criteria(
                SoftDeleteMixin,
                lambda cls: cls.deleted_at.is_(None),
                include_aliases=True,
            )
        )


engine = create_async_engine(str(get_settings().database_url), pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session
