"""The manager's products: list, create, edit (tiers, colors, image, hide/show), delete."""

from typing import Any

import pytest
from botocore.exceptions import ClientError
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import soft_delete
from app.core.storage import storage_client
from app.features.catalog import admin_service
from app.features.catalog.models import Category, ProductPriceTier
from app.features.media import service as media_service
from app.features.orders.models import Order, OrderItem
from tests.factories import add_category, add_product
from tests.media.uploads import put_tmp_image

URL = "/api/admin/products"


@pytest.fixture
async def category(db_session: AsyncSession) -> Category:
    return await add_category(db_session)


def _new(category: Category, **fields: Any) -> dict[str, Any]:
    return {
        "category_id": category.id,
        "name_ar": "ستيكر",
        "name_en": "Sticker",
        "pricing_mode": "fixed",
        "price_tiers": [{"quantity": 250, "price": "7", "note_en": "4 cm"}],
        **fields,
    }


async def _create(client: AsyncClient, category: Category, **fields: Any) -> dict[str, Any]:
    response = await client.post(URL, json=_new(category, **fields))
    assert response.status_code == 201, response.text
    created: dict[str, Any] = response.json()
    return created


async def _patch(client: AsyncClient, product_id: int, **fields: Any) -> dict[str, Any]:
    response = await client.patch(f"{URL}/{product_id}", json=fields)
    assert response.status_code == 200, response.text
    patched: dict[str, Any] = response.json()
    return patched


async def _refused(
    client: AsyncClient, method: str, path: str, body: dict[str, Any], code: str
) -> None:
    response = await client.request(method, path, json=body)
    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == code


async def _page(client: AsyncClient, **params: Any) -> dict[str, Any]:
    response = await client.get(URL, params=params)
    assert response.status_code == 200, response.text
    page: dict[str, Any] = response.json()
    return page


async def _listed(client: AsyncClient, **params: Any) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = (await _page(client, **params))["items"]
    return items


async def _listed_ids(client: AsyncClient, **params: Any) -> list[int]:
    return [product["id"] for product in await _listed(client, **params)]


async def _in_store(client: AsyncClient, product_id: int) -> bool:
    return (await client.get(f"/api/products/{product_id}")).status_code == 200


def _object_exists(key: str) -> bool:
    listing = storage_client().list_objects_v2(Bucket=get_settings().s3_bucket, Prefix=key)
    return listing.get("KeyCount", 0) > 0


def _tier(quantity: int, price: str, **fields: Any) -> dict[str, Any]:
    return {"quantity": quantity, "price": price, **fields}


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", URL),
        ("POST", URL),
        ("GET", f"{URL}/1"),
        ("PATCH", f"{URL}/1"),
        ("DELETE", f"{URL}/1"),
    ],
)
async def test_every_endpoint_needs_a_login(client: AsyncClient, method: str, path: str) -> None:
    response = await client.request(method, path, json={})

    assert response.status_code == 401


async def test_create_returns_the_whole_product(
    admin_client: AsyncClient, category: Category
) -> None:
    created = await _create(
        admin_client,
        category,
        description_en="  Glossy  ",
        free_delivery=True,
        colors=[{"name_ar": "أحمر", "name_en": "Red", "hex": "#FF0000"}],
    )

    assert created["category_id"] == category.id
    assert created["description_en"] == "Glossy"
    assert created["description_ar"] == ""
    assert created["free_delivery"] is True
    assert created["is_visible"] is True
    assert created["shown_in_store"] is True
    assert created["price"] == "7.000"
    [tier] = created["price_tiers"]
    assert tier == {
        "id": tier["id"],
        "quantity": 250,
        "price": "7.000",
        "note_ar": None,
        "note_en": "4 cm",
    }
    [color] = created["colors"]
    assert color == {"id": color["id"], "name_ar": "أحمر", "name_en": "Red", "hex": "#ff0000"}
    assert created["image_key"] is None
    assert await _in_store(admin_client, created["id"])


async def test_a_fixed_product_without_tiers_is_saved_but_not_in_the_store(
    admin_client: AsyncClient, category: Category
) -> None:
    created = await _create(admin_client, category, price_tiers=[])

    assert created["shown_in_store"] is False
    assert created["price"] is None
    assert created["id"] in await _listed_ids(admin_client)
    assert not await _in_store(admin_client, created["id"])


async def test_a_quote_product_keeps_its_tiers_but_has_no_price(
    admin_client: AsyncClient, category: Category
) -> None:
    created = await _create(admin_client, category)

    patched = await _patch(admin_client, created["id"], pricing_mode="quote")

    assert patched["price"] is None
    assert patched["price_tiers"] == created["price_tiers"]
    assert patched["shown_in_store"] is True


async def test_list_has_hidden_products_newest_first_and_filters(
    admin_client: AsyncClient, db_session: AsyncSession, category: Category
) -> None:
    other = await add_category(db_session)
    older = await add_product(db_session, category, name_en="Blue mug")
    hidden = await add_product(db_session, category, is_visible=False, name_en="Card")
    elsewhere = await add_product(db_session, other, name_en="Mug 50%")
    deleted = await add_product(db_session, category)
    await soft_delete(db_session, deleted)

    assert await _listed_ids(admin_client) == [elsewhere.id, hidden.id, older.id]
    assert await _listed_ids(admin_client, category_id=category.id) == [hidden.id, older.id]
    assert await _listed_ids(admin_client, q="MUG") == [elsewhere.id, older.id]
    assert await _listed_ids(admin_client, q="50%") == [elsewhere.id]
    assert await _listed_ids(admin_client, is_visible="false") == [hidden.id]


async def test_list_is_paged_with_a_total(
    admin_client: AsyncClient, db_session: AsyncSession, category: Category
) -> None:
    products = [await add_product(db_session, category) for _ in range(3)]
    newest_first = [product.id for product in reversed(products)]

    first = await _page(admin_client, limit=2)
    second = await _page(admin_client, limit=2, offset=2)

    assert [item["id"] for item in first["items"]] == newest_first[:2]
    assert (first["total"], first["limit"], first["offset"]) == (3, 2, 0)
    assert [item["id"] for item in second["items"]] == newest_first[2:]
    assert second["total"] == 3
    assert (await _page(admin_client))["limit"] == 50


@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 101}, {"offset": -1}, {"page": 1}])
async def test_invalid_paging_is_refused(admin_client: AsyncClient, params: dict[str, int]) -> None:
    assert (await admin_client.get(URL, params=params)).status_code == 422


async def test_get_one_returns_the_product_hidden_ones_too(
    admin_client: AsyncClient, category: Category
) -> None:
    created = await _create(admin_client, category, is_visible=False)

    response = await admin_client.get(f"{URL}/{created['id']}")

    assert response.status_code == 200
    assert response.json() == created


async def test_get_one_refuses_an_unknown_id(admin_client: AsyncClient) -> None:
    response = await admin_client.get(f"{URL}/999999")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "product_not_found"


async def test_hide_and_show_is_reflected_in_the_store(
    admin_client: AsyncClient, category: Category
) -> None:
    created = await _create(admin_client, category)

    hidden = await _patch(admin_client, created["id"], is_visible=False)
    assert hidden["is_visible"] is False
    assert hidden["shown_in_store"] is False
    assert not await _in_store(admin_client, created["id"])

    await _patch(admin_client, created["id"], is_visible=True)
    assert await _in_store(admin_client, created["id"])


async def test_edit_changes_only_the_fields_sent(
    admin_client: AsyncClient, category: Category
) -> None:
    created = await _create(admin_client, category)

    patched = await _patch(admin_client, created["id"], name_en="Big sticker")

    unchanged = {key: value for key, value in created.items() if key != "updated_at"}
    assert {key: value for key, value in patched.items() if key != "updated_at"} == {
        **unchanged,
        "name_en": "Big sticker",
    }


async def test_moving_a_product_to_another_category(
    admin_client: AsyncClient, db_session: AsyncSession, category: Category
) -> None:
    other = await add_category(db_session)
    created = await _create(admin_client, category)

    patched = await _patch(admin_client, created["id"], category_id=other.id)

    assert patched["category_id"] == other.id
    assert (await admin_client.delete(f"/api/admin/categories/{category.id}")).status_code == 204


@pytest.mark.parametrize(
    "field",
    ["category_id", "name_ar", "description_en", "pricing_mode", "is_visible", "price_tiers"],
)
async def test_edit_refuses_null_for_a_required_field(
    admin_client: AsyncClient, category: Category, field: str
) -> None:
    created = await _create(admin_client, category)

    response = await admin_client.patch(f"{URL}/{created['id']}", json={field: None})

    assert response.status_code == 422


async def test_unknown_or_deleted_category_is_refused(
    admin_client: AsyncClient, db_session: AsyncSession, category: Category
) -> None:
    gone = await add_category(db_session)
    await soft_delete(db_session, gone)
    created = await _create(admin_client, category)

    await _refused(admin_client, "POST", URL, _new(gone), "category_not_found")
    await _refused(
        admin_client,
        "PATCH",
        f"{URL}/{created['id']}",
        {"category_id": 999999},
        "category_not_found",
    )


@pytest.mark.parametrize(
    "fields",
    [
        {"pricing_mode": "free"},
        {"price_tiers": [_tier(0, "1")]},
        {"price_tiers": [_tier(1, "-1")]},
        {"price_tiers": [_tier(1, "1.0001")]},
        {"price_tiers": [_tier(1, "10000000")]},
        {"colors": [{"name_ar": "أ", "name_en": "A", "hex": "red"}]},
        {"name_en": "x" * 201},
        {"price": "1.000"},
    ],
)
async def test_invalid_product_is_refused(
    admin_client: AsyncClient, category: Category, fields: dict[str, Any]
) -> None:
    response = await admin_client.post(URL, json=_new(category, **fields))

    assert response.status_code == 422


@pytest.mark.parametrize(
    "tiers",
    [
        [_tier(250, "7"), _tier(250, "8")],
        [_tier(250, "7", note_en="4 cm"), _tier(250, "8", note_en=" 4 cm ")],
        [_tier(250, "7", note_en=""), _tier(250, "8")],
    ],
)
async def test_an_exact_duplicate_tier_is_refused(
    admin_client: AsyncClient, category: Category, tiers: list[dict[str, Any]]
) -> None:
    await _refused(
        admin_client, "POST", URL, _new(category, price_tiers=tiers), "duplicate_price_tier"
    )


async def test_the_same_quantity_with_another_note_is_allowed(
    admin_client: AsyncClient, category: Category
) -> None:
    tiers = [_tier(250, "7", note_en="4 cm"), _tier(250, "9", note_en="6 cm")]

    created = await _create(admin_client, category, price_tiers=tiers)

    assert [tier["note_en"] for tier in created["price_tiers"]] == ["4 cm", "6 cm"]


async def test_sent_tiers_replace_the_table_and_keep_ids_of_matched_rows(
    admin_client: AsyncClient, category: Category
) -> None:
    created = await _create(
        admin_client, category, price_tiers=[_tier(100, "4"), _tier(250, "7"), _tier(500, "12")]
    )
    small, middle, _ = created["price_tiers"]

    patched = await _patch(
        admin_client,
        created["id"],
        price_tiers=[
            {**middle, "price": "6.500"},
            {**small, "quantity": 150},
            _tier(1000, "20"),
        ],
    )

    rows = {tier["quantity"]: tier for tier in patched["price_tiers"]}
    assert sorted(rows) == [150, 250, 1000]
    assert rows[250]["id"] == middle["id"]
    assert rows[250]["price"] == "6.500"
    assert rows[150]["id"] == small["id"]
    assert rows[1000]["id"] not in {tier["id"] for tier in created["price_tiers"]}
    assert patched["price"] == "4.000"
    detail = (await admin_client.get(f"/api/products/{created['id']}")).json()
    assert [tier["quantity"] for tier in detail["price_tiers"]] == [150, 250, 1000]


async def test_removing_and_adding_back_the_same_tier_works(
    admin_client: AsyncClient, category: Category
) -> None:
    created = await _create(admin_client, category, price_tiers=[_tier(100, "4")])

    patched = await _patch(admin_client, created["id"], price_tiers=[_tier(100, "5")])

    [tier] = patched["price_tiers"]
    assert tier["price"] == "5.000"
    assert tier["id"] != created["price_tiers"][0]["id"]


async def test_tiers_swapping_quantities_are_saved(
    admin_client: AsyncClient, category: Category
) -> None:
    created = await _create(admin_client, category, price_tiers=[_tier(100, "4"), _tier(200, "7")])
    first, second = created["price_tiers"]

    patched = await _patch(
        admin_client,
        created["id"],
        price_tiers=[{**first, "quantity": 200}, {**second, "quantity": 100}],
    )

    assert [(tier["quantity"], tier["price"]) for tier in patched["price_tiers"]] == [
        (100, "7.000"),
        (200, "4.000"),
    ]


async def test_a_tier_id_of_another_product_is_refused(
    admin_client: AsyncClient, category: Category
) -> None:
    mine = await _create(admin_client, category)
    theirs = await _create(admin_client, category)

    await _refused(
        admin_client,
        "PATCH",
        f"{URL}/{mine['id']}",
        {"price_tiers": theirs["price_tiers"]},
        "price_tier_not_found",
    )
    await _refused(
        admin_client,
        "POST",
        URL,
        _new(category, price_tiers=mine["price_tiers"]),
        "price_tier_not_found",
    )


async def test_sent_colors_replace_the_list_in_order_and_keep_ids(
    admin_client: AsyncClient, category: Category
) -> None:
    red = {"name_ar": "أحمر", "name_en": "Red", "hex": "#ff0000"}
    blue = {"name_ar": "أزرق", "name_en": "Blue", "hex": "#0000ff"}
    created = await _create(admin_client, category, colors=[red, blue])
    red_out, blue_out = created["colors"]

    patched = await _patch(
        admin_client,
        created["id"],
        colors=[
            {**blue_out, "name_en": "Navy"},
            {"name_ar": "أخضر", "name_en": "Green", "hex": "#00ff00"},
        ],
    )

    assert [color["name_en"] for color in patched["colors"]] == ["Navy", "Green"]
    assert patched["colors"][0]["id"] == blue_out["id"]
    assert red_out["id"] not in {color["id"] for color in patched["colors"]}

    cleared = await _patch(admin_client, created["id"], colors=[])
    assert cleared["colors"] == []
    detail = (await admin_client.get(f"/api/products/{created['id']}")).json()
    assert detail["colors"] == []


async def test_a_refused_edit_changes_nothing(
    admin_client: AsyncClient, category: Category
) -> None:
    created = await _create(admin_client, category)

    await _refused(
        admin_client,
        "PATCH",
        f"{URL}/{created['id']}",
        {"name_en": "Changed", "price_tiers": [{"id": 999999, "quantity": 1, "price": "1"}]},
        "price_tier_not_found",
    )

    [listed] = await _listed(admin_client)
    assert listed == created


async def test_delete_removes_the_product_from_the_dashboard_and_store(
    admin_client: AsyncClient, category: Category
) -> None:
    created = await _create(admin_client, category)

    response = await admin_client.delete(f"{URL}/{created['id']}")

    assert response.status_code == 204
    assert await _listed_ids(admin_client) == []
    assert not await _in_store(admin_client, created["id"])
    assert (await admin_client.delete(f"{URL}/{created['id']}")).status_code == 404
    assert (await admin_client.get(f"{URL}/{created['id']}")).status_code == 404
    assert (await admin_client.patch(f"{URL}/{created['id']}", json={})).status_code == 404


async def test_a_failed_delete_of_the_old_image_does_not_fail_the_save(
    admin_client: AsyncClient,
    category: Category,
    empty_bucket: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created = await _create(admin_client, category, image_key=put_tmp_image())
    old = created["image_key"]

    async def _storage_down(image_key: str) -> None:
        raise ClientError({"Error": {"Code": "ServiceUnavailable"}}, "DeleteObject")

    monkeypatch.setattr(media_service, "delete_image", _storage_down)
    patched = await _patch(admin_client, created["id"], image_key=put_tmp_image())

    new = patched["image_key"]
    assert new != old
    assert _object_exists(new)
    assert _object_exists(old)  # left behind, logged
    [listed] = await _listed(admin_client)
    assert listed["image_key"] == new


async def test_image_is_saved_replaced_and_kept_after_delete(
    admin_client: AsyncClient, category: Category, empty_bucket: str
) -> None:
    created = await _create(admin_client, category, image_key=put_tmp_image())
    first = created["image_key"]
    assert first.startswith("media/")
    assert _object_exists(first)

    kept = await _patch(admin_client, created["id"], image_key=first, name_en="Renamed")
    assert kept["image_key"] == first
    assert _object_exists(first)

    replaced = await _patch(admin_client, created["id"], image_key=put_tmp_image())
    second = replaced["image_key"]
    assert replaced["image_url"] == f"/{second}"
    assert _object_exists(second)
    assert not _object_exists(first)

    await admin_client.delete(f"{URL}/{created['id']}")
    assert _object_exists(second)


async def test_invalid_image_key_is_refused(
    admin_client: AsyncClient, category: Category, empty_bucket: str
) -> None:
    await _refused(
        admin_client, "POST", URL, _new(category, image_key="tmp/x.png"), "invalid_image_key"
    )
    assert await _listed_ids(admin_client) == []


async def test_a_refused_edit_does_not_move_the_upload(
    admin_client: AsyncClient, category: Category, empty_bucket: str
) -> None:
    created = await _create(admin_client, category)
    upload = put_tmp_image()

    await _refused(
        admin_client,
        "PATCH",
        f"{URL}/{created['id']}",
        {"image_key": upload, "category_id": 999999},
        "category_not_found",
    )

    assert _object_exists(upload)


async def test_the_same_upload_sent_twice_is_refused_the_second_time(
    admin_client: AsyncClient, category: Category, empty_bucket: str
) -> None:
    upload = put_tmp_image()
    first = await _create(admin_client, category, image_key=upload)

    await _refused(admin_client, "POST", URL, _new(category, image_key=upload), "image_in_use")

    assert await _listed_ids(admin_client) == [first["id"]]
    assert _object_exists(first["image_key"])


async def test_an_upload_key_forged_from_another_rows_image_is_refused(
    admin_client: AsyncClient, category: Category, empty_bucket: str
) -> None:
    owner = await _create(admin_client, category, image_key=put_tmp_image())
    other = await _create(admin_client, category)
    forged = owner["image_key"].replace("media/", "tmp/", 1)

    await _refused(
        admin_client, "PATCH", f"{URL}/{other['id']}", {"image_key": forged}, "image_in_use"
    )
    await admin_client.delete(f"{URL}/{owner['id']}")
    await _refused(admin_client, "POST", URL, _new(category, image_key=forged), "image_in_use")

    assert _object_exists(owner["image_key"])


async def test_a_retried_save_with_the_same_upload_succeeds(
    admin_client: AsyncClient, category: Category, empty_bucket: str
) -> None:
    created = await _create(admin_client, category)
    upload = put_tmp_image()

    first = await _patch(admin_client, created["id"], image_key=upload)
    again = await _patch(admin_client, created["id"], image_key=upload)

    assert again["image_key"] == first["image_key"]
    assert _object_exists(first["image_key"])


async def test_a_create_whose_first_attempt_never_committed_can_be_retried(
    admin_client: AsyncClient, category: Category, empty_bucket: str
) -> None:
    upload = put_tmp_image()
    moved = await media_service.save_image(upload)  # the first attempt moved it, then failed

    created = await _create(admin_client, category, image_key=upload)

    assert created["image_key"] == moved


async def test_a_tier_added_by_an_overlapping_save_is_a_clean_409(
    admin_client: AsyncClient,
    category: Category,
    empty_bucket: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created = await _create(admin_client, category)
    # Skip the in-request check, as when two saves add the same tier at the same moment:
    # only the unique index sees the clash.
    monkeypatch.setattr(admin_service, "find_duplicate", lambda keys: None)
    upload = put_tmp_image()

    response = await admin_client.patch(
        f"{URL}/{created['id']}",
        json={"image_key": upload, "price_tiers": [_tier(5, "1"), _tier(5, "2")]},
    )

    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "duplicate_price_tier"
    assert _object_exists(upload)  # the clash came before the image was moved
    [listed] = await _listed(admin_client)
    assert listed["price_tiers"] == created["price_tiers"]


async def test_an_image_moved_by_a_failed_save_is_deleted_again(
    admin_client: AsyncClient,
    category: Category,
    empty_bucket: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created = await _create(admin_client, category, image_key=put_tmp_image())
    old = created["image_key"]
    upload = put_tmp_image()

    async def _commit_fails(self: AsyncSession) -> None:
        raise RuntimeError("database went away")

    with monkeypatch.context() as patch:
        patch.setattr(AsyncSession, "commit", _commit_fails)
        with pytest.raises(RuntimeError):
            await admin_client.patch(f"{URL}/{created['id']}", json={"image_key": upload})

    assert not _object_exists(upload.replace("tmp/", "media/", 1))
    assert _object_exists(old)
    [listed] = await _listed(admin_client)
    assert listed["image_key"] == old


# Old orders


async def _place_order(client: AsyncClient, product: dict[str, Any]) -> int:
    body = {
        "customer_name": "Qusai",
        "phone": "0791234567",
        "governorate": "amman",
        "address": "Street 1",
        "items": [
            {
                "product_id": product["id"],
                "tier_id": product["price_tiers"][0]["id"],
                "color_id": product["colors"][0]["id"],
                "item_count": 2,
            }
        ],
    }
    response = await client.post("/api/orders", json=body)
    assert response.status_code == 201, response.text
    order_id: int = response.json()["id"]
    return order_id


async def _stored_order(session: AsyncSession, order_id: int) -> list[dict[str, Any]]:
    """Every column of the order and its items, as stored."""
    order = (
        await session.execute(select(Order.__table__).where(Order.__table__.c.id == order_id))
    ).one()
    items = await session.execute(
        select(OrderItem.__table__)
        .where(OrderItem.__table__.c.order_id == order_id)
        .order_by(OrderItem.__table__.c.id)
    )
    return [dict(order._mapping), *(dict(item._mapping) for item in items)]


async def test_old_orders_stay_the_same_after_a_product_edit_and_delete(
    admin_client: AsyncClient, db_session: AsyncSession, category: Category, empty_bucket: str
) -> None:
    product = await _create(
        admin_client,
        category,
        image_key=put_tmp_image(),
        colors=[{"name_ar": "أحمر", "name_en": "Red", "hex": "#ff0000"}],
    )
    order_id = await _place_order(admin_client, product)
    before = await _stored_order(db_session, order_id)
    assert before[1]["unit_price"] is not None

    await _patch(
        admin_client,
        product["id"],
        name_ar="اسم جديد",
        name_en="New name",
        pricing_mode="quote",
        image_key=put_tmp_image(),
        price_tiers=[{**product["price_tiers"][0], "price": "99", "note_en": "changed"}],
        colors=[{**product["colors"][0], "name_en": "Crimson", "hex": "#990000"}],
    )
    assert await _stored_order(db_session, order_id) == before

    await _patch(admin_client, product["id"], price_tiers=[], colors=[])
    assert await _stored_order(db_session, order_id) == before
    removed_tier = await db_session.scalar(
        select(ProductPriceTier.deleted_at)
        .where(ProductPriceTier.id == product["price_tiers"][0]["id"])
        .execution_options(include_deleted=True)
    )
    assert removed_tier is not None

    response = await admin_client.delete(f"{URL}/{product['id']}")
    assert response.status_code == 204
    assert await _stored_order(db_session, order_id) == before
