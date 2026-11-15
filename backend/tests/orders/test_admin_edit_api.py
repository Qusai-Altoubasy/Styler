"""One order in the dashboard: details, the mark, the note, quote prices, delete."""

from decimal import Decimal
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import INCLUDE_DELETED
from app.features.orders.enums import OrderStatus
from app.features.orders.models import Order, OrderItem
from app.features.settings.service import get_store_settings
from tests.factories import add_order, fixed_item, quote_item


def _url(order: Order | int) -> str:
    return f"/api/admin/orders/{order if isinstance(order, int) else order.id}"


async def _patch(admin_client: AsyncClient, order: Order, body: dict[str, Any]) -> dict[str, Any]:
    response = await admin_client.patch(_url(order), json=body)
    assert response.status_code == 200, response.text
    detail: dict[str, Any] = response.json()
    return detail


async def _refused(
    admin_client: AsyncClient, order: Order, body: dict[str, Any], code: str
) -> dict[str, Any]:
    response = await admin_client.patch(_url(order), json=body)
    assert response.status_code == 422, response.text
    error: dict[str, Any] = response.json()["error"]
    assert error["code"] == code
    return error


async def _get(admin_client: AsyncClient, order: Order) -> dict[str, Any]:
    response = await admin_client.get(_url(order))
    assert response.status_code == 200, response.text
    detail: dict[str, Any] = response.json()
    return detail


def _price(order: Order, item: OrderItem, price: str | None) -> dict[str, Any]:
    return {"item_prices": [{"item_id": item.id, "unit_price": price}]}


async def test_details_have_everything_the_manager_needs(
    admin_client: AsyncClient, db_session: AsyncSession
) -> None:
    fixed = fixed_item(
        "7.000",
        2,
        quantity=250,
        tier_note_ar="٤ سم",
        tier_note_en="4 cm",
        color_name_ar="أحمر",
        color_name_en="Red",
        color_hex="#ff0000",
    )
    quote = quote_item(quantity=300)
    order = await add_order(
        db_session,
        fixed,
        quote,
        customer_name="Qusai",
        phone="0791234567",
        address="Street 9",
        internal_note="call after 5",
    )

    detail = await _get(admin_client, order)

    assert detail["id"] == order.id
    assert detail["customer_name"] == "Qusai"
    assert detail["phone"] == "0791234567"
    assert detail["whatsapp_number"] == "962791234567"
    assert detail["governorate"] == "irbid"
    assert detail["address"] == "Street 9"
    assert (detail["delivery_fee"], detail["subtotal"], detail["total"]) == (
        "3.000",
        "14.000",
        "17.000",
    )
    assert detail["awaiting_quote"] is True
    assert detail["internal_note"] == "call after 5"
    assert detail["status"] is None
    first, second = detail["items"]
    assert first["id"] == fixed.id
    assert (first["quantity"], first["tier_note_en"], first["color_name_en"]) == (
        250,
        "4 cm",
        "Red",
    )
    assert (first["pricing_mode"], first["unit_price"], first["item_count"]) == (
        "fixed",
        "7.000",
        2,
    )
    assert first["line_total"] == "14.000"
    assert (second["pricing_mode"], second["quantity"], second["unit_price"]) == (
        "quote",
        300,
        None,
    )
    assert second["line_total"] is None


async def test_unknown_order_is_404_and_out_of_range_id_is_422(
    admin_client: AsyncClient,
) -> None:
    for method in ("GET", "PATCH", "DELETE"):
        body: dict[str, Any] | None = {} if method == "PATCH" else None
        response = await admin_client.request(method, _url(999_999), json=body)
        assert response.status_code == 404, method
        assert response.json()["error"]["code"] == "order_not_found"
        response = await admin_client.request(method, _url(2**31), json=body)
        assert response.status_code == 422, method


async def test_mark_is_set_switched_and_cleared(
    admin_client: AsyncClient, db_session: AsyncSession
) -> None:
    order = await add_order(db_session)

    assert (await _patch(admin_client, order, {"status": "done"}))["status"] == "done"
    assert (await _patch(admin_client, order, {"status": "cancelled"}))["status"] == "cancelled"
    assert (await _patch(admin_client, order, {}))["status"] == "cancelled"
    assert (await _patch(admin_client, order, {"internal_note": "x"}))["status"] == "cancelled"
    assert (await _patch(admin_client, order, {"status": None}))["status"] is None
    assert (await _get(admin_client, order))["status"] is None

    response = await admin_client.patch(_url(order), json={"status": "new"})
    assert response.status_code == 422


async def test_internal_note_is_set_kept_and_cleared(
    admin_client: AsyncClient, db_session: AsyncSession
) -> None:
    order = await add_order(db_session)

    detail = await _patch(admin_client, order, {"internal_note": "  design approved\nline 2 "})
    assert detail["internal_note"] == "design approved\nline 2"
    detail = await _patch(admin_client, order, {"status": "done"})
    assert detail["internal_note"] == "design approved\nline 2"
    assert (await _patch(admin_client, order, {"internal_note": " "}))["internal_note"] is None
    await _patch(admin_client, order, {"internal_note": "again"})
    assert (await _patch(admin_client, order, {"internal_note": None}))["internal_note"] is None

    for note in ("a\x00b", "x" * 2001):
        response = await admin_client.patch(_url(order), json={"internal_note": note})
        assert response.status_code == 422


async def test_pricing_a_quote_item_recalculates_a_mixed_order_and_keeps_delivery(
    admin_client: AsyncClient, db_session: AsyncSession
) -> None:
    store = await get_store_settings(db_session)
    store.zone_b_delivery_fee = Decimal("9.000")  # changed after the order was placed
    await db_session.flush()
    quote = quote_item(item_count=3)
    order = await add_order(db_session, fixed_item("5.000", 2), quote, delivery_fee="3.000")

    detail = await _patch(admin_client, order, _price(order, quote, "2.5"))

    assert (detail["delivery_fee"], detail["subtotal"], detail["total"]) == (
        "3.000",
        "17.500",
        "20.500",
    )
    assert detail["awaiting_quote"] is False
    priced = detail["items"][1]
    assert (priced["unit_price"], priced["line_total"]) == ("2.500", "7.500")
    stored = await db_session.scalar(
        select(Order).where(Order.id == order.id).execution_options(populate_existing=True)
    )
    assert stored is not None
    assert (stored.subtotal, stored.total) == (Decimal("17.500"), Decimal("20.500"))


async def test_pricing_keeps_free_delivery(
    admin_client: AsyncClient, db_session: AsyncSession
) -> None:
    quote = quote_item(item_count=2)
    order = await add_order(db_session, quote, delivery_fee="0.000")

    detail = await _patch(admin_client, order, _price(order, quote, "4.000"))

    assert (detail["delivery_fee"], detail["subtotal"], detail["total"]) == (
        "0.000",
        "8.000",
        "8.000",
    )


async def test_clearing_a_price_takes_the_item_out_of_the_totals(
    admin_client: AsyncClient, db_session: AsyncSession
) -> None:
    first, second = quote_item(), quote_item()
    order = await add_order(db_session, first, second)

    detail = await _patch(
        admin_client,
        order,
        {
            "item_prices": [
                {"item_id": first.id, "unit_price": "1.000"},
                {"item_id": second.id, "unit_price": "2.000"},
            ]
        },
    )
    assert (detail["subtotal"], detail["total"], detail["awaiting_quote"]) == (
        "3.000",
        "6.000",
        False,
    )

    detail = await _patch(admin_client, order, _price(order, second, None))

    assert (detail["subtotal"], detail["total"], detail["awaiting_quote"]) == (
        "1.000",
        "4.000",
        True,
    )
    assert detail["items"][1]["unit_price"] is None


async def test_a_quote_item_can_be_priced_at_zero(
    admin_client: AsyncClient, db_session: AsyncSession
) -> None:
    quote = quote_item()
    order = await add_order(db_session, quote)

    detail = await _patch(admin_client, order, _price(order, quote, "0"))

    assert detail["items"][0]["unit_price"] == "0.000"
    assert detail["awaiting_quote"] is False


async def test_a_fixed_item_price_is_refused_and_nothing_changes(
    admin_client: AsyncClient, db_session: AsyncSession
) -> None:
    fixed = fixed_item("5.000")
    quote = quote_item()
    order = await add_order(db_session, fixed, quote)

    error = await _refused(
        admin_client,
        order,
        {
            "status": "done",
            "item_prices": [
                {"item_id": quote.id, "unit_price": "1.000"},
                {"item_id": fixed.id, "unit_price": "1.000"},
            ],
        },
        "item_price_fixed",
    )

    assert error["details"] == {"item_id": fixed.id}
    detail = await _get(admin_client, order)
    assert detail["status"] is None
    assert [item["unit_price"] for item in detail["items"]] == ["5.000", None]
    assert detail["total"] == "8.000"


async def test_an_item_of_another_order_is_refused(
    admin_client: AsyncClient, db_session: AsyncSession
) -> None:
    order = await add_order(db_session, quote_item())
    foreign = quote_item()
    await add_order(db_session, foreign)

    error = await _refused(
        admin_client, order, _price(order, foreign, "1.000"), "order_item_not_found"
    )

    assert error["details"] == {"item_id": foreign.id}


@pytest.mark.parametrize(
    "body",
    [
        {"item_prices": [{"item_id": 1, "unit_price": "-1.000"}]},
        {"item_prices": [{"item_id": 1, "unit_price": "1.0001"}]},
        {"item_prices": [{"item_id": 1, "unit_price": "10000000"}]},
        {"item_prices": [{"item_id": 1}]},
        {"item_prices": [{"item_id": 2**31, "unit_price": "1.000"}]},
        {
            "item_prices": [
                {"item_id": 1, "unit_price": "1.000"},
                {"item_id": 1, "unit_price": "2.000"},
            ]
        },
        {"total": "1.000"},
        {"delivery_fee": "0.000"},
    ],
)
async def test_malformed_edits_are_refused(
    admin_client: AsyncClient, db_session: AsyncSession, body: dict[str, Any]
) -> None:
    order = await add_order(db_session)

    response = await admin_client.patch(_url(order), json=body)

    assert response.status_code == 422, response.text
    assert "detail" in response.json()


async def test_a_price_that_overflows_the_total_is_refused(
    admin_client: AsyncClient, db_session: AsyncSession
) -> None:
    quote = quote_item(item_count=10_000)
    order = await add_order(db_session, quote)

    await _refused(admin_client, order, _price(order, quote, "9999.000"), "order_too_large")

    assert (await _get(admin_client, order))["items"][0]["unit_price"] is None


async def test_delete_hides_the_order_everywhere(
    admin_client: AsyncClient, db_session: AsyncSession
) -> None:
    order = await add_order(db_session, fixed_item("5.000"), quote_item(), status=OrderStatus.DONE)
    kept = await add_order(db_session)

    response = await admin_client.delete(_url(order))

    assert response.status_code == 204
    assert (await admin_client.get(_url(order))).status_code == 404
    assert (await admin_client.patch(_url(order), json={"status": "done"})).status_code == 404
    assert (await admin_client.delete(_url(order))).status_code == 404
    page = (await admin_client.get("/api/admin/orders")).json()
    assert [row["id"] for row in page["items"]] == [kept.id]
    stats = (await admin_client.get("/api/admin/orders/stats")).json()
    assert (stats["all_orders"], stats["quote_orders"], stats["orders_value"]) == (
        1,
        0,
        "8.000",
    )
    stored = await db_session.scalar(
        select(Order)
        .where(Order.id == order.id)
        .execution_options(**{INCLUDE_DELETED: True}, populate_existing=True)
    )
    assert stored is not None
    assert stored.deleted_at is not None
    items = await db_session.scalars(
        select(OrderItem)
        .where(OrderItem.order_id == order.id)
        .execution_options(**{INCLUDE_DELETED: True}, populate_existing=True)
    )
    deleted_at = [item.deleted_at for item in items]
    assert len(deleted_at) == 2
    assert all(moment is not None for moment in deleted_at)
