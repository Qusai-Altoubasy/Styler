"""The manager's categories: list, create, edit, delete."""

from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import soft_delete
from app.core.storage import storage_client
from tests.factories import add_category, add_product
from tests.media.uploads import put_tmp_image

URL = "/api/admin/categories"


def _new(**fields: Any) -> dict[str, Any]:
    return {"name_ar": "أكواب", "name_en": "Mugs", "color": "magenta", **fields}


async def _create(client: AsyncClient, **fields: Any) -> dict[str, Any]:
    response = await client.post(URL, json=_new(**fields))
    assert response.status_code == 201, response.text
    created: dict[str, Any] = response.json()
    return created


async def _listed(client: AsyncClient) -> dict[int, dict[str, Any]]:
    response = await client.get(URL)
    assert response.status_code == 200, response.text
    return {category["id"]: category for category in response.json()}


def _object_exists(key: str) -> bool:
    listing = storage_client().list_objects_v2(Bucket=get_settings().s3_bucket, Prefix=key)
    return listing.get("KeyCount", 0) > 0


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", URL),
        ("POST", URL),
        ("PATCH", f"{URL}/1"),
        ("DELETE", f"{URL}/1"),
    ],
)
async def test_every_endpoint_needs_a_login(client: AsyncClient, method: str, path: str) -> None:
    response = await client.request(method, path, json=_new())

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_authenticated"


async def test_create_returns_the_category_and_strips_names(admin_client: AsyncClient) -> None:
    created = await _create(admin_client, name_en="  Mugs  ", sort_order=3)

    assert created == {
        "id": created["id"],
        "name_ar": "أكواب",
        "name_en": "Mugs",
        "color": "magenta",
        "image_key": None,
        "image_url": None,
        "sort_order": 3,
        "product_count": 0,
    }


async def test_list_has_every_category_with_all_live_products_counted(
    admin_client: AsyncClient, db_session: AsyncSession
) -> None:
    empty = await add_category(db_session, sort_order=2)
    used = await add_category(db_session, sort_order=1)
    await add_product(db_session, used, tiers=[(1, "1.000")])
    await add_product(db_session, used, is_visible=False)
    await add_product(db_session, used)  # fixed without tiers is still counted below
    deleted = await add_product(db_session, used)
    await soft_delete(db_session, deleted)
    gone = await add_category(db_session)
    await soft_delete(db_session, gone)

    listed = await _listed(admin_client)

    assert listed[empty.id]["product_count"] == 0
    assert listed[used.id]["product_count"] == 3
    assert gone.id not in listed
    ids = list(listed)
    assert ids.index(used.id) < ids.index(empty.id)


async def test_edit_changes_only_the_fields_sent(admin_client: AsyncClient) -> None:
    created = await _create(admin_client)

    response = await admin_client.patch(f"{URL}/{created['id']}", json={"color": "yellow"})

    assert response.status_code == 200, response.text
    assert response.json() == {**created, "color": "yellow"}


@pytest.mark.parametrize("field", ["name_ar", "name_en", "color", "sort_order"])
async def test_edit_refuses_null_for_a_required_field(
    admin_client: AsyncClient, field: str
) -> None:
    created = await _create(admin_client)

    response = await admin_client.patch(f"{URL}/{created['id']}", json={field: None})

    assert response.status_code == 422


@pytest.mark.parametrize(
    "body",
    [
        _new(color="red"),
        _new(name_ar="   "),
        _new(name_en="x" * 101),
        _new(name_en="Mu\x00gs"),
        _new(unknown=1),
    ],
)
async def test_invalid_category_is_refused(admin_client: AsyncClient, body: dict[str, Any]) -> None:
    response = await admin_client.post(URL, json=body)

    assert response.status_code == 422


@pytest.mark.parametrize(
    ("taken", "field"),
    [({"name_en": " MUGS "}, "name_en"), ({"name_ar": "  أكواب"}, "name_ar")],
)
async def test_duplicate_name_ignoring_case_and_spaces_is_409(
    admin_client: AsyncClient, taken: dict[str, str], field: str
) -> None:
    await _create(admin_client)
    other = {"name_ar": "غيره", "name_en": "Other", **taken}

    response = await admin_client.post(URL, json=_new(**other))

    assert response.status_code == 409, response.text
    assert response.json()["error"] == {
        "code": "category_name_taken",
        "message": "A category with this name exists",
        "details": {"field": field},
    }


async def test_renaming_to_a_taken_name_is_409_and_changes_nothing(
    admin_client: AsyncClient,
) -> None:
    await _create(admin_client)
    other = await _create(admin_client, name_ar="غيره", name_en="Other")

    response = await admin_client.patch(f"{URL}/{other['id']}", json={"name_en": "mugs"})

    assert response.status_code == 409
    assert (await _listed(admin_client))[other["id"]]["name_en"] == "Other"


async def test_a_deleted_categorys_name_can_be_used_again(admin_client: AsyncClient) -> None:
    first = await _create(admin_client)
    assert (await admin_client.delete(f"{URL}/{first['id']}")).status_code == 204

    second = await _create(admin_client)

    assert second["id"] != first["id"]


async def test_a_category_with_products_cannot_be_deleted(
    admin_client: AsyncClient, db_session: AsyncSession
) -> None:
    category = await add_category(db_session)
    await add_product(db_session, category, is_visible=False)

    response = await admin_client.delete(f"{URL}/{category.id}")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "category_has_products"
    assert response.json()["error"]["details"] == {"product_count": 1}
    assert category.id in await _listed(admin_client)


async def test_a_category_whose_products_were_deleted_can_be_deleted(
    admin_client: AsyncClient, db_session: AsyncSession
) -> None:
    category = await add_category(db_session)
    product = await add_product(db_session, category)
    await soft_delete(db_session, product)

    response = await admin_client.delete(f"{URL}/{category.id}")

    assert response.status_code == 204
    assert category.id not in await _listed(admin_client)


async def test_unknown_category_is_404(admin_client: AsyncClient) -> None:
    patched = await admin_client.patch(f"{URL}/999999", json={"color": "cyan"})
    deleted = await admin_client.delete(f"{URL}/999999")

    assert patched.status_code == deleted.status_code == 404
    assert patched.json()["error"]["code"] == "category_not_found"


async def test_image_is_moved_to_media_and_replacing_it_deletes_the_old_one(
    admin_client: AsyncClient, empty_bucket: str
) -> None:
    first_upload = put_tmp_image()
    created = await _create(admin_client, image_key=first_upload)
    first = created["image_key"]

    assert first == first_upload.replace("tmp/", "media/", 1)
    assert created["image_url"] == f"/{first}"
    assert _object_exists(first)
    assert not _object_exists(first_upload)

    second_upload = put_tmp_image()
    response = await admin_client.patch(f"{URL}/{created['id']}", json={"image_key": second_upload})

    assert response.status_code == 200, response.text
    second = response.json()["image_key"]
    assert _object_exists(second)
    assert not _object_exists(first)


async def test_resending_the_current_image_keeps_it_and_null_removes_it(
    admin_client: AsyncClient, empty_bucket: str
) -> None:
    created = await _create(admin_client, image_key=put_tmp_image())
    key = created["image_key"]

    kept = await admin_client.patch(f"{URL}/{created['id']}", json={"image_key": key})
    assert kept.json()["image_key"] == key
    assert _object_exists(key)

    removed = await admin_client.patch(f"{URL}/{created['id']}", json={"image_key": None})
    assert removed.json()["image_key"] is None
    assert not _object_exists(key)


async def test_deleting_a_category_keeps_its_image(
    admin_client: AsyncClient, empty_bucket: str
) -> None:
    created = await _create(admin_client, image_key=put_tmp_image())

    await admin_client.delete(f"{URL}/{created['id']}")

    assert _object_exists(created["image_key"])


@pytest.mark.parametrize(
    ("image_key", "code"),
    [
        ("media/../secret.webp", "invalid_image_key"),
        ("tmp/00000000-0000-4000-8000-000000000000.webp", "image_not_uploaded"),
        # Another row's saved image: sharing one object would lose it on replace.
        ("media/00000000-0000-4000-8000-000000000000.webp", "invalid_image_key"),
    ],
)
async def test_unusable_image_key_is_422(
    admin_client: AsyncClient, empty_bucket: str, image_key: str, code: str
) -> None:
    response = await admin_client.post(URL, json=_new(image_key=image_key))

    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == code
    assert await _listed(admin_client) == {}
