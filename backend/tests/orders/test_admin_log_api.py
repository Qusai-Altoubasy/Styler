"""The manager's order log: login, the list (mark filter, search, pages) and the stats."""

from datetime import datetime, timedelta
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import soft_delete
from app.features.orders.enums import OrderStatus
from tests.factories import add_order, fixed_item, quote_item


async def _list(admin_client: AsyncClient, **params: Any) -> dict[str, Any]:
    response = await admin_client.get("/api/admin/orders", params=params)
    assert response.status_code == 200, response.text
    page: dict[str, Any] = response.json()
    return page


async def _ids(admin_client: AsyncClient, **params: Any) -> list[int]:
    return [row["id"] for row in (await _list(admin_client, **params))["items"]]


async def _stats(admin_client: AsyncClient) -> dict[str, Any]:
    response = await admin_client.get("/api/admin/orders/stats")
    assert response.status_code == 200, response.text
    stats: dict[str, Any] = response.json()
    return stats


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/api/admin/orders"),
        ("GET", "/api/admin/orders/stats"),
        ("GET", "/api/admin/orders/1001"),
        ("PATCH", "/api/admin/orders/1001"),
        ("DELETE", "/api/admin/orders/1001"),
    ],
)
async def test_every_order_endpoint_needs_a_login(
    client: AsyncClient, method: str, path: str
) -> None:
    response = await client.request(method, path, json={} if method == "PATCH" else None)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_authenticated"


async def test_list_is_newest_first_with_the_table_columns(
    admin_client: AsyncClient, db_session: AsyncSession
) -> None:
    older = await add_order(db_session)
    newer = await add_order(
        db_session,
        fixed_item("5.000", 2, product_name_ar="تيشيرت", product_name_en="T-shirt"),
        quote_item(product_name_ar="ستيكر", product_name_en="Sticker"),
        customer_name="Qusai",
        phone="0781112222",
        status=OrderStatus.DONE,
    )

    page = await _list(admin_client)

    assert [row["id"] for row in page["items"]] == [newer.id, older.id]
    assert (page["total"], page["limit"], page["offset"]) == (2, 50, 0)
    row = page["items"][0]
    assert row["customer_name"] == "Qusai"
    assert row["phone"] == "0781112222"
    assert row["governorate"] == "irbid"
    assert row["total"] == "13.000"
    assert row["status"] == "done"
    assert row["awaiting_quote"] is True
    assert row["products"] == [
        {"product_name_ar": "تيشيرت", "product_name_en": "T-shirt", "item_count": 2},
        {"product_name_ar": "ستيكر", "product_name_en": "Sticker", "item_count": 1},
    ]
    assert "internal_note" not in row
    assert page["items"][1]["awaiting_quote"] is False
    assert page["items"][1]["status"] is None


async def test_list_filters_by_mark(admin_client: AsyncClient, db_session: AsyncSession) -> None:
    unmarked = await add_order(db_session)
    done = await add_order(db_session, status=OrderStatus.DONE)
    cancelled = await add_order(db_session, status=OrderStatus.CANCELLED)

    assert await _ids(admin_client) == [cancelled.id, done.id, unmarked.id]
    assert await _ids(admin_client, status="all") == [cancelled.id, done.id, unmarked.id]
    assert await _ids(admin_client, status="unmarked") == [unmarked.id]
    assert await _ids(admin_client, status="done") == [done.id]
    assert await _ids(admin_client, status="cancelled") == [cancelled.id]
    assert (await _list(admin_client, status="done"))["total"] == 1
    bad = await admin_client.get("/api/admin/orders", params={"status": "new"})
    assert bad.status_code == 422


async def test_search_by_name_ignores_case(
    admin_client: AsyncClient, db_session: AsyncSession
) -> None:
    qusai = await add_order(db_session, customer_name="Qusai Altoubasy")
    await add_order(db_session, customer_name="Ahmad")
    arabic = await add_order(db_session, customer_name="قصي الطوباسي")

    assert await _ids(admin_client, q="altou") == [qusai.id]
    assert await _ids(admin_client, q="  QUSAI ") == [qusai.id]
    assert await _ids(admin_client, q="قصي") == [arabic.id]
    assert await _ids(admin_client, q="50%_") == []


@pytest.mark.parametrize(
    "typed",
    [
        "0791234567",  # the whole number
        "1234567",  # part of it
        "079 123-4567",  # spaces and dashes
        "٠٧٩١٢٣٤٥٦٧",  # Arabic-Indic digits
        "۰۷۹ ۱۲۳",  # Persian digits, partial
        "+962 79 123 4567",  # international form
        "962791234567",
    ],
)
async def test_search_by_phone_as_the_manager_types_it(
    admin_client: AsyncClient, db_session: AsyncSession, typed: str
) -> None:
    wanted = await add_order(db_session, phone="0791234567")
    await add_order(db_session, phone="0780000000")

    assert await _ids(admin_client, q=typed) == [wanted.id]


async def test_search_by_order_number(admin_client: AsyncClient, db_session: AsyncSession) -> None:
    await add_order(db_session, phone="0770000000")
    wanted = await add_order(db_session, phone="0770000000")
    await add_order(db_session, phone="0770000000")

    assert await _ids(admin_client, q=str(wanted.id)) == [wanted.id]
    assert await _ids(admin_client, q=f" {wanted.id} ") == [wanted.id]


async def test_search_with_a_number_beyond_any_id_finds_nothing(
    admin_client: AsyncClient, db_session: AsyncSession
) -> None:
    await add_order(db_session, phone="0770000000")

    assert await _ids(admin_client, q="99999999999999999999") == []
    assert await _ids(admin_client, q=str(2**31)) == []


async def test_search_refuses_control_characters_and_long_text(admin_client: AsyncClient) -> None:
    for q in ("a\x00b", "x" * 101):
        response = await admin_client.get("/api/admin/orders", params={"q": q})
        assert response.status_code == 422


async def test_list_pages_with_a_total_count(
    admin_client: AsyncClient, db_session: AsyncSession
) -> None:
    first = await add_order(db_session)
    second = await add_order(db_session)
    third = await add_order(db_session)

    page = await _list(admin_client, limit=2)
    assert [row["id"] for row in page["items"]] == [third.id, second.id]
    assert page["total"] == 3
    page = await _list(admin_client, limit=2, offset=2)
    assert [row["id"] for row in page["items"]] == [first.id]
    assert page["total"] == 3

    for params in ({"limit": 0}, {"limit": 101}, {"offset": -1}, {"offset": 10**12}):
        response = await admin_client.get("/api/admin/orders", params=params)
        assert response.status_code == 422, params


async def test_list_leaves_out_deleted_orders(
    admin_client: AsyncClient, db_session: AsyncSession
) -> None:
    live = await add_order(db_session)
    deleted = await add_order(db_session)
    await soft_delete(db_session, deleted)

    page = await _list(admin_client)

    assert [row["id"] for row in page["items"]] == [live.id]
    assert page["total"] == 1


async def test_stats_of_an_empty_log(admin_client: AsyncClient) -> None:
    assert await _stats(admin_client) == {
        "all_orders": 0,
        "today_orders": 0,
        "quote_orders": 0,
        "orders_value": "0.000",
    }


async def test_orders_value_leaves_out_cancelled_and_deleted_orders(
    admin_client: AsyncClient, db_session: AsyncSession
) -> None:
    await add_order(db_session, fixed_item("10.000"))  # 13.000, unmarked
    await add_order(db_session, fixed_item("20.000"), status=OrderStatus.DONE)  # 23.000
    await add_order(db_session, fixed_item("100.000"), status=OrderStatus.CANCELLED)
    deleted = await add_order(db_session, fixed_item("1000.000"))
    await soft_delete(db_session, deleted)

    stats = await _stats(admin_client)

    assert stats["orders_value"] == "36.000"
    assert stats["all_orders"] == 3
    assert stats["all_orders"] == (await _list(admin_client))["total"]


async def test_quote_orders_counts_orders_with_any_quote_item(
    admin_client: AsyncClient, db_session: AsyncSession
) -> None:
    await add_order(db_session, fixed_item("5.000"), quote_item())  # mixed, unpriced
    await add_order(db_session, quote_item(), quote_item(), status=OrderStatus.CANCELLED)
    await add_order(db_session, quote_item("4.000"))  # priced already: still a quote order
    await add_order(db_session, fixed_item("5.000"))
    deleted = await add_order(db_session, quote_item())
    await soft_delete(db_session, deleted)

    stats = await _stats(admin_client)

    assert stats["quote_orders"] == 3
    assert stats["all_orders"] == 4


async def _amman_midnight(session: AsyncSession) -> datetime:
    """The start of today in Jordan, as PostgreSQL sees it."""
    midnight = await session.scalar(
        text("SELECT date_trunc('day', now() AT TIME ZONE 'Asia/Amman') AT TIME ZONE 'Asia/Amman'")
    )
    assert isinstance(midnight, datetime)
    return midnight


async def test_today_is_the_calendar_day_in_amman(
    admin_client: AsyncClient, db_session: AsyncSession
) -> None:
    midnight = await _amman_midnight(db_session)
    await add_order(db_session, created_at=midnight - timedelta(seconds=1))  # yesterday
    await add_order(db_session, created_at=midnight)
    await add_order(db_session, created_at=midnight + timedelta(minutes=1))
    await add_order(db_session, created_at=midnight - timedelta(days=3))
    await add_order(db_session, created_at=midnight, status=OrderStatus.CANCELLED)
    deleted = await add_order(db_session, created_at=midnight)
    await soft_delete(db_session, deleted)

    stats = await _stats(admin_client)

    assert stats["today_orders"] == 3
    assert stats["all_orders"] == 5
