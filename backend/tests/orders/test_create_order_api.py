"""Placing an order: prices and delivery are computed on the server."""

from decimal import Decimal
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.db import soft_delete
from app.features.catalog.models import Product
from app.features.orders.models import Order
from app.features.settings.service import get_store_settings
from app.shared.pricing_mode import PricingMode
from tests.factories import add_product


@pytest.fixture(autouse=True)
async def delivery_fees(db_session: AsyncSession) -> None:
    store = await get_store_settings(db_session)
    store.zone_a_delivery_fee = Decimal("2.000")
    store.zone_b_delivery_fee = Decimal("3.000")
    await db_session.flush()


def _order(*items: dict[str, Any], **fields: Any) -> dict[str, Any]:
    return {
        "customer_name": "  Qusai  ",
        "phone": "0791234567",
        "governorate": "irbid",
        "address": "Street 1",
        "items": list(items),
        **fields,
    }


async def _place(client: AsyncClient, body: dict[str, Any]) -> dict[str, Any]:
    response = await client.post("/api/orders", json=body)
    assert response.status_code == 201, response.text
    placed: dict[str, Any] = response.json()
    return placed


async def _refused(client: AsyncClient, body: dict[str, Any], code: str) -> None:
    response = await client.post("/api/orders", json=body)
    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == code


def _tier_id(product: Product, quantity: int) -> int:
    return next(tier.id for tier in product.price_tiers if tier.quantity == quantity)


async def test_fixed_order_is_priced_from_the_tier_with_zone_b_delivery(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    product = await add_product(db_session, tiers=[(100, "4.000"), (250, "7.000")])

    body = await _place(
        client,
        _order({"product_id": product.id, "tier_id": _tier_id(product, 250), "item_count": 2}),
    )

    assert body["customer_name"] == "Qusai"
    assert body["delivery_fee"] == "3.000"
    assert body["subtotal"] == "14.000"
    assert body["total"] == "17.000"
    assert body["awaiting_quote"] is False
    [item] = body["items"]
    assert (item["quantity"], item["unit_price"], item["line_total"]) == (250, "7.000", "14.000")
    stored = await db_session.get(Order, body["id"])
    assert stored is not None
    assert stored.total == Decimal("17.000")


async def test_amman_and_zarqa_pay_the_zone_a_fee(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    product = await add_product(db_session, tiers=[(1, "5.000")])
    item = {"product_id": product.id, "tier_id": _tier_id(product, 1)}

    for governorate in ("amman", "zarqa"):
        body = await _place(client, _order(item, governorate=governorate))
        assert body["delivery_fee"] == "2.000"
        assert body["total"] == "7.000"


async def test_quote_order_has_no_price_and_keeps_the_approximate_quantity(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    product = await add_product(db_session)

    body = await _place(client, _order({"product_id": product.id, "approx_quantity": 300}))

    [item] = body["items"]
    assert (item["quantity"], item["unit_price"], item["line_total"]) == (300, None, None)
    assert body["subtotal"] == "0.000"
    assert body["total"] == "3.000"
    assert body["awaiting_quote"] is True


async def test_mixed_order_totals_the_priced_items_only(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    fixed = await add_product(db_session, tiers=[(50, "6.500")])
    quote = await add_product(db_session)

    body = await _place(
        client,
        _order(
            {"product_id": fixed.id, "tier_id": _tier_id(fixed, 50), "item_count": 2},
            {"product_id": quote.id},
        ),
    )

    assert body["subtotal"] == "13.000"
    assert body["total"] == "16.000"
    assert body["awaiting_quote"] is True


async def test_one_free_delivery_product_makes_the_whole_order_free_to_deliver(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    normal = await add_product(db_session, tiers=[(1, "5.000")])
    free = await add_product(db_session, tiers=[(1, "30.000")], free_delivery=True)

    body = await _place(
        client,
        _order(
            {"product_id": normal.id, "tier_id": _tier_id(normal, 1)},
            {"product_id": free.id, "tier_id": _tier_id(free, 1)},
        ),
    )

    assert body["delivery_fee"] == "0.000"
    assert body["total"] == "35.000"


async def test_prices_sent_by_the_browser_are_refused(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    product = await add_product(db_session, tiers=[(1, "5.000")])
    item = {"product_id": product.id, "tier_id": _tier_id(product, 1), "unit_price": "0.001"}

    response = await client.post("/api/orders", json=_order(item, total="0.001"))

    assert response.status_code == 422


@pytest.mark.parametrize(
    ("typed", "stored"),
    [
        ("0791234567", "0791234567"),
        ("0771234567", "0771234567"),
        ("0781234567", "0781234567"),
        ("079 123 4567", "0791234567"),
        ("079-123-4567", "0791234567"),
        ("٠٧٩١٢٣٤٥٦٧", "0791234567"),
        ("۰۷۸ ۱۲۳ ۴۵۶۷", "0781234567"),
        (" 078 12-34 567 ", "0781234567"),
    ],
)
async def test_phone_is_accepted_and_stored_as_plain_digits(
    client: AsyncClient, db_session: AsyncSession, typed: str, stored: str
) -> None:
    product = await add_product(db_session)

    body = await _place(client, _order({"product_id": product.id}, phone=typed))

    assert body["phone"] == stored
    order = await db_session.get(Order, body["id"])
    assert order is not None
    assert order.phone == stored


@pytest.mark.parametrize(
    "phone", ["0761234567", "079123456", "07912345678", "+962791234567", "0791234abc", ""]
)
async def test_other_phone_numbers_are_refused(
    client: AsyncClient, db_session: AsyncSession, phone: str
) -> None:
    product = await add_product(db_session)

    response = await client.post(
        "/api/orders", json=_order({"product_id": product.id}, phone=phone)
    )

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "phone"]


async def test_order_needs_at_least_one_item(client: AsyncClient) -> None:
    response = await client.post("/api/orders", json=_order())

    assert response.status_code == 422


async def test_hidden_or_deleted_products_cannot_be_ordered(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    hidden = await add_product(db_session, is_visible=False)
    deleted = await add_product(db_session)
    await soft_delete(db_session, deleted)

    await _refused(client, _order({"product_id": hidden.id}), "product_unavailable")
    await _refused(client, _order({"product_id": deleted.id}), "product_unavailable")


async def test_fixed_product_needs_one_of_its_own_live_tiers(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    product = await add_product(db_session, tiers=[(1, "5.000"), (2, "9.000")])
    other = await add_product(db_session, tiers=[(1, "1.000")])
    removed = product.price_tiers[1]
    await soft_delete(db_session, removed)

    await _refused(client, _order({"product_id": product.id}), "tier_required")
    await _refused(
        client,
        _order({"product_id": product.id, "tier_id": _tier_id(other, 1)}),
        "tier_not_found",
    )
    await _refused(
        client, _order({"product_id": product.id, "tier_id": removed.id}), "tier_not_found"
    )
    await _refused(
        client,
        _order({"product_id": product.id, "tier_id": _tier_id(product, 1), "approx_quantity": 5}),
        "approx_quantity_not_allowed",
    )


async def test_color_is_required_only_when_the_product_has_colors(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    colored = await add_product(db_session, colors=[("أحمر", "#ff0000")])
    plain = await add_product(db_session)
    red = colored.colors[0]

    await _refused(client, _order({"product_id": colored.id}), "color_required")
    await _refused(
        client, _order({"product_id": colored.id, "color_id": red.id + 999}), "color_not_found"
    )
    await _refused(
        client, _order({"product_id": plain.id, "color_id": red.id}), "color_not_allowed"
    )
    body = await _place(client, _order({"product_id": colored.id, "color_id": red.id}))
    assert body["items"][0]["color_hex"] == "#ff0000"


async def test_editing_or_deleting_a_product_leaves_old_orders_unchanged(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    product = await add_product(
        db_session, tiers=[(100, "4.000")], colors=[("أحمر", "#ff0000")], name_ar="كوب"
    )
    body = await _place(
        client,
        _order(
            {
                "product_id": product.id,
                "tier_id": _tier_id(product, 100),
                "color_id": product.colors[0].id,
            }
        ),
    )

    product.name_ar = "كوب جديد"
    product.price_tiers[0].price = Decimal("99.000")
    product.colors[0].hex = "#00ff00"
    await db_session.flush()
    await soft_delete(db_session, product)

    stored = await db_session.scalar(
        select(Order)
        .where(Order.id == body["id"])
        .options(selectinload(Order.items))
        .execution_options(populate_existing=True)
    )
    assert stored is not None
    [item] = stored.items
    assert item.product_name_ar == "كوب"
    assert item.unit_price == Decimal("4.000")
    assert item.color_hex == "#ff0000"
    assert stored.total == Decimal("7.000")


async def test_out_of_range_product_id_is_refused_not_a_server_error(
    client: AsyncClient,
) -> None:
    response = await client.post("/api/orders", json=_order({"product_id": 2**31}))

    assert response.status_code == 422


@pytest.mark.parametrize("field", ["customer_name", "address"])
async def test_control_characters_in_text_are_refused(
    client: AsyncClient, db_session: AsyncSession, field: str
) -> None:
    product = await add_product(db_session)
    body = _order({"product_id": product.id}, **{field: "Qusai\x00"})

    response = await client.post("/api/orders", json=body)

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", field]


async def test_address_may_span_several_lines(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    product = await add_product(db_session)

    body = await _place(client, _order({"product_id": product.id}, address="Irbid\nStreet 1"))

    assert body["address"] == "Irbid\nStreet 1"


async def test_fixed_product_without_tiers_cannot_be_ordered(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    product = await add_product(db_session, pricing_mode=PricingMode.FIXED)

    await _refused(client, _order({"product_id": product.id}), "product_unavailable")


async def test_order_above_the_largest_storable_total_is_refused(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    product = await add_product(db_session, tiers=[(1, "5000000.000")])
    item = {"product_id": product.id, "tier_id": _tier_id(product, 1), "item_count": 2}

    await _refused(client, _order(item), "order_too_large")
