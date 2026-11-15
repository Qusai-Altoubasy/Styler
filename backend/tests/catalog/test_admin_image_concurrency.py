"""The same upload saved twice at once (a double tap), on two real connections.

Unlike the other tests, these rows are committed (a lock is only visible between
separate transactions), so the fixture deletes them afterwards.
"""

import asyncio
from collections.abc import AsyncIterator

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import INCLUDE_DELETED, SessionLocal
from app.core.storage import storage_client
from app.features.catalog import admin_service
from app.features.catalog.admin_schemas import ProductCreate
from app.features.catalog.admin_service import ImageInUseError
from app.features.catalog.enums import BrandColor
from app.features.catalog.models import Category, Product
from app.shared.pricing_mode import PricingMode
from tests.media.uploads import put_tmp_image

BLOCKED_FOR = 0.3
"""How long the second save is given to (wrongly) get past the first one's lock."""


@pytest.fixture
async def committed_category(empty_bucket: str) -> AsyncIterator[int]:
    """A committed category; it and every product in it are removed for good afterwards."""
    async with SessionLocal() as session:
        category = Category(name_ar="تزامن", name_en="Concurrency", color=BrandColor.CYAN)
        session.add(category)
        await session.commit()
        category_id = category.id
    yield category_id
    async with SessionLocal() as session:
        await session.execute(
            delete(Product)
            .where(Product.category_id == category_id)
            .execution_options(**{INCLUDE_DELETED: True})
        )
        await session.execute(
            delete(Category)
            .where(Category.id == category_id)
            .execution_options(**{INCLUDE_DELETED: True})
        )
        await session.commit()


def _product(category_id: int, image_key: str) -> ProductCreate:
    return ProductCreate(
        category_id=category_id,
        name_ar="منتج",
        name_en="Product",
        pricing_mode=PricingMode.QUOTE,
        image_key=image_key,
    )


async def _paused_before_commit(session: AsyncSession, gate: asyncio.Event) -> asyncio.Event:
    """Make `session.commit()` wait for `gate`; the returned event is set once it waits,
    i.e. once the save has moved the image and holds its lock."""
    waiting = asyncio.Event()
    commit = session.commit

    async def paused_commit() -> None:
        waiting.set()
        await gate.wait()
        await commit()

    session.commit = paused_commit  # type: ignore[method-assign]
    return waiting


def _object_exists(key: str) -> bool:
    listing = storage_client().list_objects_v2(Bucket=get_settings().s3_bucket, Prefix=key)
    return listing.get("KeyCount", 0) > 0


async def test_a_double_tapped_create_waits_and_is_refused(committed_category: int) -> None:
    upload = put_tmp_image()
    gate = asyncio.Event()
    async with SessionLocal() as first_tap, SessionLocal() as second_tap:
        first_waiting = await _paused_before_commit(first_tap, gate)
        first = asyncio.create_task(
            admin_service.create_product(first_tap, _product(committed_category, upload))
        )
        await asyncio.wait_for(first_waiting.wait(), timeout=5)

        second = asyncio.create_task(
            admin_service.create_product(second_tap, _product(committed_category, upload))
        )
        await asyncio.sleep(BLOCKED_FOR)
        assert not second.done(), "the second save must wait for the first one's lock"

        gate.set()
        saved = await asyncio.wait_for(first, timeout=5)
        with pytest.raises(ImageInUseError):
            await asyncio.wait_for(second, timeout=5)

    assert saved.image_key is not None
    assert _object_exists(saved.image_key)
    async with SessionLocal() as session:
        owners = list(
            await session.scalars(
                select(Product.id)
                .where(Product.image_key == saved.image_key)
                .execution_options(**{INCLUDE_DELETED: True})
            )
        )
    assert owners == [saved.id]
