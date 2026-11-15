"""`POST /api/admin/media/upload-url` and the policy it signs, tried against MinIO."""

from typing import Any

from httpx import AsyncClient

from app.core.config import get_settings
from app.core.storage import storage_client
from app.features.media.keys import MAX_UPLOAD_BYTES, parse_image_key
from tests.media.uploads import SMALL_WEBP, post_upload

UPLOAD_URL = "/api/admin/media/upload-url"


async def _upload_url(admin_client: AsyncClient) -> dict[str, Any]:
    response = await admin_client.post(UPLOAD_URL, json={"content_type": "image/webp"})
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


async def test_needs_a_session(client: AsyncClient) -> None:
    response = await client.post(UPLOAD_URL, json={"content_type": "image/webp"})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_authenticated"


async def test_answers_a_presigned_post_for_a_fresh_tmp_key(admin_client: AsyncClient) -> None:
    first = await _upload_url(admin_client)
    second = await _upload_url(admin_client)

    key = parse_image_key(first["key"])
    assert key is not None and not key.is_saved
    assert first["key"] != second["key"]
    assert first["fields"]["key"] == first["key"]
    assert first["fields"]["Content-Type"] == "image/webp"
    assert "policy" in first["fields"]
    assert first["url"].startswith(get_settings().s3_public_endpoint_url)
    assert first["max_bytes"] == MAX_UPLOAD_BYTES
    assert first["expires_in_seconds"] == 300


async def test_only_webp_may_be_asked_for(admin_client: AsyncClient) -> None:
    for content_type in ("image/png", "image/jpeg", "image/svg+xml", "text/html", ""):
        response = await admin_client.post(UPLOAD_URL, json={"content_type": content_type})
        assert response.status_code == 422, content_type


async def test_unknown_fields_are_refused(admin_client: AsyncClient) -> None:
    response = await admin_client.post(
        UPLOAD_URL, json={"content_type": "image/webp", "key": "media/x.webp"}
    )

    assert response.status_code == 422


async def test_the_policy_accepts_a_small_webp(admin_client: AsyncClient) -> None:
    upload = await _upload_url(admin_client)

    response = await post_upload(upload["url"], upload["fields"], SMALL_WEBP)

    assert response.status_code == 204, response.text
    stored = storage_client().head_object(Bucket=get_settings().s3_bucket, Key=upload["key"])
    assert stored["ContentType"] == "image/webp"
    assert stored["ContentLength"] == len(SMALL_WEBP)


async def test_the_policy_refuses_a_file_over_the_limit(admin_client: AsyncClient) -> None:
    upload = await _upload_url(admin_client)

    response = await post_upload(upload["url"], upload["fields"], bytes(MAX_UPLOAD_BYTES + 1))

    assert response.status_code == 400
    assert "EntityTooLarge" in response.text


async def test_the_policy_refuses_an_empty_file(admin_client: AsyncClient) -> None:
    upload = await _upload_url(admin_client)

    response = await post_upload(upload["url"], upload["fields"], b"")

    assert response.status_code == 400
    assert "EntityTooSmall" in response.text


async def test_the_policy_refuses_another_content_type(admin_client: AsyncClient) -> None:
    upload = await _upload_url(admin_client)
    fields = {**upload["fields"], "Content-Type": "text/html"}

    response = await post_upload(upload["url"], fields, b"<script></script>", "text/html")

    assert response.status_code == 403


async def test_the_policy_refuses_another_key(admin_client: AsyncClient) -> None:
    upload = await _upload_url(admin_client)
    other = parse_image_key(upload["key"])
    assert other is not None
    fields = {**upload["fields"], "key": other.media_key}

    response = await post_upload(upload["url"], fields, SMALL_WEBP)

    assert response.status_code == 403
