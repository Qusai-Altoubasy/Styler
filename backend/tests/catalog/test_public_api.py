"""The storefront's catalog: only visible, live rows, with prices from the tiers."""

from typing import Any

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import soft_delete
from app.shared.pricing_mode import PricingMode
from tests.factories import add_category, add_product


async def _category_cards(client: AsyncClient) -> dict[int, dict[str, Any]]:
    response = await client.get("/api/categories")
    assert response.status_code == 200
    return {card["id"]: card for card in response.json()}


async def _product_ids(client: AsyncClient, **params: str | int) -> list[int]:
    response = await client.get("/api/products", params=params)
    assert response.status_code == 200, response.text
    return [card["id"] for card in response.json()]


async def test_category_card_counts_visible_products_and_shows_lowest_price(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    category = await add_category(db_session)
    await add_product(db_session, category, tiers=[(100, "9.000"), (250, "7.000")])
    await add_product(db_session, category, tiers=[(50, "12.000")])
    await add_product(db_session, category)  # quote: counted, no price
    await add_product(db_session, category, tiers=[(1, "1.000")], is_visible=False)
    deleted = await add_product(db_session, category, tiers=[(1, "0.500")])
    await soft_delete(db_session, deleted)

    card = (await _category_cards(client))[category.id]

    assert card["product_count"] == 3
    assert card["min_price"] == "7.000"


async def test_category_without_visible_products_is_hidden(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    empty = await add_category(db_session)
    only_hidden = await add_category(db_session)
    await add_product(db_session, only_hidden, is_visible=False)

    cards = await _category_cards(client)

    assert empty.id not in cards
    assert only_hidden.id not in cards


async def test_category_with_only_quote_products_has_no_price(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    category = await add_category(db_session)
    await add_product(db_session, category)

    assert (await _category_cards(client))[category.id]["min_price"] is None


async def test_soft_deleted_tier_is_left_out_of_prices_and_details(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    product = await add_product(db_session, tiers=[(100, "1.000"), (200, "5.000")])
    cheap = next(tier for tier in product.price_tiers if tier.quantity == 100)
    await soft_delete(db_session, cheap)

    detail = (await client.get(f"/api/products/{product.id}")).json()
    card = (await _category_cards(client))[product.category_id]

    assert [tier["quantity"] for tier in detail["price_tiers"]] == [200]
    assert detail["price"] == "5.000"
    assert card["min_price"] == "5.000"


async def test_hidden_product_is_not_listed_and_its_page_is_404(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    hidden = await add_product(db_session, tiers=[(1, "1.000")], is_visible=False)

    assert hidden.id not in await _product_ids(client)
    response = await client.get(f"/api/products/{hidden.id}")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "product_not_found"


async def test_product_detail_has_tiers_colors_and_category(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    product = await add_product(
        db_session,
        tiers=[(250, "7.000"), (100, "4.000")],
        colors=[("أحمر", "#ff0000"), ("أزرق", "#0000ff")],
    )
    deleted_color = product.colors[1]
    await soft_delete(db_session, deleted_color)

    body = (await client.get(f"/api/products/{product.id}")).json()

    assert body["category"]["id"] == product.category_id
    assert [(t["quantity"], t["price"]) for t in body["price_tiers"]] == [
        (100, "4.000"),
        (250, "7.000"),
    ]
    assert [color["hex"] for color in body["colors"]] == ["#ff0000"]
    assert body["price"] == "4.000"


async def test_products_filter_by_category_mode_and_free_delivery(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    category = await add_category(db_session)
    fixed = await add_product(db_session, category, tiers=[(1, "5.000")])
    quote = await add_product(db_session, category, free_delivery=True)
    elsewhere = await add_product(db_session, tiers=[(1, "5.000")])

    assert set(await _product_ids(client, category_id=category.id)) == {fixed.id, quote.id}
    in_category = await _product_ids(client, category_id=category.id, pricing_mode="quote")
    assert in_category == [quote.id]
    free = await _product_ids(client, free_delivery="true")
    assert quote.id in free
    assert fixed.id not in free
    assert elsewhere.id not in free


async def test_price_filter_uses_the_lowest_tier_and_hides_quote_products(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    category = await add_category(db_session)
    cheap = await add_product(db_session, category, tiers=[(1, "3.000"), (10, "20.000")])
    pricey = await add_product(db_session, category, tiers=[(1, "15.000")])
    quote = await add_product(db_session, category)

    ids = await _product_ids(client, category_id=category.id, min_price="0", max_price="10")

    assert ids == [cheap.id]
    assert pricey.id not in ids
    assert quote.id not in ids


async def test_price_sorting_puts_quote_products_last_both_ways(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    category = await add_category(db_session)
    quote = await add_product(db_session, category)
    mid = await add_product(db_session, category, tiers=[(1, "5.000")])
    low = await add_product(db_session, category, tiers=[(1, "2.000")])
    high = await add_product(db_session, category, tiers=[(1, "9.000")])

    ascending = await _product_ids(client, category_id=category.id, sort="price_asc")
    descending = await _product_ids(client, category_id=category.id, sort="price_desc")

    assert ascending == [low.id, mid.id, high.id, quote.id]
    assert descending == [high.id, mid.id, low.id, quote.id]


async def test_name_sorting_follows_the_language(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    category = await add_category(db_session)
    first_ar = await add_product(db_session, category, name_ar="أ منتج", name_en="Z product")
    first_en = await add_product(db_session, category, name_ar="ي منتج", name_en="A product")

    by_ar = await _product_ids(client, category_id=category.id, sort="name", lang="ar")
    by_en = await _product_ids(client, category_id=category.id, sort="name", lang="en")

    assert by_ar == [first_ar.id, first_en.id]
    assert by_en == [first_en.id, first_ar.id]


async def test_name_sorting_ignores_letter_case(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    category = await add_category(db_session)
    zebra = await add_product(db_session, category, name_en="Zebra stickers")
    apple = await add_product(db_session, category, name_en="apple mug")

    by_en = await _product_ids(client, category_id=category.id, sort="name", lang="en")

    assert by_en == [apple.id, zebra.id]


async def test_search_matches_either_name_and_treats_wildcards_literally(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    category = await add_category(db_session)
    mug = await add_product(db_session, category, name_ar="كوب حراري", name_en="Thermal Mug")
    sale = await add_product(db_session, category, name_ar="عرض", name_en="Pack 50% off")

    assert await _product_ids(client, category_id=category.id, q="mug") == [mug.id]
    assert await _product_ids(client, category_id=category.id, q="حراري") == [mug.id]
    assert await _product_ids(client, category_id=category.id, q="50%") == [sale.id]
    assert await _product_ids(client, category_id=category.id, q="%") == [sale.id]


async def test_product_card_says_whether_it_has_live_colors(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    category = await add_category(db_session)
    colored = await add_product(db_session, category, colors=[("أحمر", "#ff0000")])
    faded = await add_product(db_session, category, colors=[("أزرق", "#0000ff")])
    await soft_delete(db_session, faded.colors[0])

    cards = {
        card["id"]: card
        for card in (await client.get("/api/products", params={"category_id": category.id})).json()
    }

    assert cards[colored.id]["has_colors"] is True
    assert cards[faded.id]["has_colors"] is False


async def test_quote_product_with_leftover_tiers_has_no_price(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    category = await add_category(db_session)
    switched = await add_product(
        db_session, category, tiers=[(250, "7.000")], pricing_mode=PricingMode.QUOTE
    )

    card = (await _category_cards(client))[category.id]
    detail = (await client.get(f"/api/products/{switched.id}")).json()
    priced = await _product_ids(client, category_id=category.id, max_price="100")

    assert card["min_price"] is None
    assert (detail["price"], detail["price_tiers"]) == (None, [])
    assert switched.id not in priced


async def test_fixed_product_without_live_tiers_is_not_in_the_store(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    category = await add_category(db_session)
    never_priced = await add_product(db_session, category, pricing_mode=PricingMode.FIXED)
    emptied = await add_product(db_session, category, tiers=[(1, "5.000")])
    await soft_delete(db_session, emptied.price_tiers[0])

    assert await _product_ids(client, category_id=category.id) == []
    assert category.id not in await _category_cards(client)
    for product in (never_priced, emptied):
        assert (await client.get(f"/api/products/{product.id}")).status_code == 404


async def test_out_of_range_ids_are_refused_not_a_server_error(client: AsyncClient) -> None:
    too_big = 2**31

    assert (await client.get(f"/api/products/{too_big}")).status_code == 422
    assert (await client.get("/api/products/0")).status_code == 422
    response = await client.get("/api/products", params={"category_id": too_big})
    assert response.status_code == 422


async def test_search_with_control_characters_is_refused(client: AsyncClient) -> None:
    response = await client.get("/api/products", params={"q": "mug\x00"})

    assert response.status_code == 422
