from sqlalchemy import CursorResult, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import INCLUDE_DELETED, soft_delete
from app.features.catalog.enums import BrandColor
from app.features.catalog.models import Category


async def _add_category(session: AsyncSession, name: str) -> Category:
    category = Category(name_ar=name, name_en=name, color=BrandColor.CYAN)
    session.add(category)
    await session.flush()
    return category


async def test_queries_skip_soft_deleted_rows(db_session: AsyncSession) -> None:
    category = await _add_category(db_session, "مؤقت")
    category.deleted_at = func.now()
    await db_session.flush()

    found = await db_session.scalar(select(Category).where(Category.id == category.id))

    assert found is None


async def test_include_deleted_option_shows_soft_deleted_rows(db_session: AsyncSession) -> None:
    category = await _add_category(db_session, "مؤقت")
    category.deleted_at = func.now()
    await db_session.flush()

    found = await db_session.scalar(
        select(Category)
        .where(Category.id == category.id)
        .execution_options(**{INCLUDE_DELETED: True})
    )

    assert found is not None


async def test_soft_delete_hides_the_row_from_session_get(db_session: AsyncSession) -> None:
    category = await _add_category(db_session, "مؤقت")
    category_id = category.id

    await soft_delete(db_session, category)

    assert category.deleted_at is not None
    assert await db_session.get(Category, category_id) is None


async def test_bulk_update_skips_soft_deleted_rows(db_session: AsyncSession) -> None:
    deleted = await _add_category(db_session, "محذوف")
    live = await _add_category(db_session, "موجود")
    ids = [deleted.id, live.id]
    await soft_delete(db_session, deleted)

    result = await db_session.execute(
        update(Category).where(Category.id.in_(ids)).values(sort_order=5)
    )

    assert isinstance(result, CursorResult)
    assert result.rowcount == 1


async def test_updated_at_is_readable_after_an_update(db_session: AsyncSession) -> None:
    category = await _add_category(db_session, "قبل")
    category.name_ar = "بعد"
    await db_session.flush()

    assert category.updated_at >= category.created_at
