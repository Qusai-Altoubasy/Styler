"""Two edits of one order at the same time, on two real connections.

Unlike the other tests, these rows are committed (a lock is only visible between
separate transactions), so the fixture deletes them afterwards.
"""

import asyncio
from collections.abc import AsyncIterator
from decimal import Decimal

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import INCLUDE_DELETED, SessionLocal
from app.features.orders import service
from app.features.orders.models import Order, OrderItem
from app.features.orders.schemas import ItemPriceIn, OrderUpdate
from tests.factories import add_order, fixed_item, quote_item

BLOCKED_FOR = 0.3
"""How long the second edit is given to (wrongly) get past the first one's lock."""


@pytest.fixture
async def committed_orders() -> AsyncIterator[list[int]]:
    """Ids of orders a test commits; removed for good afterwards."""
    ids: list[int] = []
    yield ids
    async with SessionLocal() as session:
        await session.execute(
            delete(OrderItem)
            .where(OrderItem.order_id.in_(ids))
            .execution_options(**{INCLUDE_DELETED: True})
        )
        await session.execute(
            delete(Order).where(Order.id.in_(ids)).execution_options(**{INCLUDE_DELETED: True})
        )
        await session.commit()


def _price(item_id: int, price: str) -> OrderUpdate:
    return OrderUpdate(item_prices=[ItemPriceIn(item_id=item_id, unit_price=Decimal(price))])


async def _paused_before_commit(session: AsyncSession, gate: asyncio.Event) -> asyncio.Event:
    """Make `session.commit()` wait for `gate`; the returned event is set once it waits,
    i.e. once the edit has read the order and computed its totals."""
    waiting = asyncio.Event()
    commit = session.commit

    async def paused_commit() -> None:
        waiting.set()
        await gate.wait()
        await commit()

    session.commit = paused_commit  # type: ignore[method-assign]
    return waiting


async def test_overlapping_price_edits_keep_both_prices_in_the_total(
    committed_orders: list[int],
) -> None:
    async with SessionLocal() as session:
        first, second = quote_item(item_count=2), quote_item(item_count=3)
        order = await add_order(session, fixed_item("5.000"), first, second, delivery_fee="3.000")
        await session.commit()
        committed_orders.append(order.id)

    gate = asyncio.Event()
    async with SessionLocal() as phone, SessionLocal() as laptop:
        phone_waiting = await _paused_before_commit(phone, gate)
        phone_edit = asyncio.create_task(
            service.update_order(phone, order.id, _price(first.id, "1.000"))
        )
        await asyncio.wait_for(phone_waiting.wait(), timeout=5)

        laptop_edit = asyncio.create_task(
            service.update_order(laptop, order.id, _price(second.id, "2.000"))
        )
        await asyncio.sleep(BLOCKED_FOR)
        assert not laptop_edit.done(), "the second edit must wait for the first one's lock"

        gate.set()
        await asyncio.wait_for(asyncio.gather(phone_edit, laptop_edit), timeout=5)

    async with SessionLocal() as session:
        stored = await session.scalar(select(Order).where(Order.id == order.id))
        prices = list(
            await session.scalars(
                select(OrderItem.unit_price)
                .where(OrderItem.order_id == order.id)
                .order_by(OrderItem.id)
            )
        )
    assert prices == [Decimal("5.000"), Decimal("1.000"), Decimal("2.000")]
    assert stored is not None
    # 5.000 + 1.000 x 2 + 2.000 x 3 = 13.000, plus 3.000 delivery.
    assert (stored.subtotal, stored.total) == (Decimal("13.000"), Decimal("16.000"))


async def test_delete_waits_for_an_edit_in_progress(committed_orders: list[int]) -> None:
    async with SessionLocal() as session:
        quote = quote_item()
        order = await add_order(session, quote)
        await session.commit()
        committed_orders.append(order.id)

    gate = asyncio.Event()
    async with SessionLocal() as editing, SessionLocal() as deleting:
        edit_waiting = await _paused_before_commit(editing, gate)
        edit = asyncio.create_task(
            service.update_order(editing, order.id, _price(quote.id, "4.000"))
        )
        await asyncio.wait_for(edit_waiting.wait(), timeout=5)

        removal = asyncio.create_task(service.delete_order(deleting, order.id))
        await asyncio.sleep(BLOCKED_FOR)
        assert not removal.done(), "the delete must wait for the edit's lock"

        gate.set()
        await asyncio.wait_for(asyncio.gather(edit, removal), timeout=5)

    async with SessionLocal() as session:
        assert await session.scalar(select(Order).where(Order.id == order.id)) is None
