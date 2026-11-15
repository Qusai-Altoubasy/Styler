"""Saving and deleting images in the bucket, against MinIO."""

import pytest
from botocore.exceptions import ClientError

from app.core.config import get_settings
from app.core.storage import storage_client
from app.features.media import service
from app.features.media.keys import new_upload_key, parse_image_key
from tests.media.uploads import SMALL_WEBP, post_upload, put_tmp_image


def _exists(key: str) -> bool:
    try:
        storage_client().head_object(Bucket=get_settings().s3_bucket, Key=key)
    except ClientError:
        return False
    return True


async def _uploaded_tmp_key() -> str:
    upload = await service.create_upload_url("image/webp")
    response = await post_upload(upload.url, upload.fields, SMALL_WEBP)
    assert response.status_code == 204, response.text
    return upload.key


def _media_key_of(tmp_key: str) -> str:
    key = parse_image_key(tmp_key)
    assert key is not None
    return key.media_key


async def test_save_moves_the_upload_to_media() -> None:
    tmp_key = await _uploaded_tmp_key()

    saved = await service.save_image(tmp_key)

    assert saved == _media_key_of(tmp_key)
    assert not _exists(tmp_key)
    stored = storage_client().get_object(Bucket=get_settings().s3_bucket, Key=saved)
    assert stored["Body"].read() == SMALL_WEBP
    assert stored["ContentType"] == "image/webp"
    assert stored["CacheControl"] == service.SAVED_IMAGE_CACHE_CONTROL


async def test_a_media_key_is_kept_without_touching_the_storage() -> None:
    key = _media_key_of(new_upload_key())

    assert await service.save_image(key) == key
    assert not _exists(key)


async def test_saving_twice_returns_the_same_media_key() -> None:
    """A retry after a save that moved the image but failed to commit."""
    tmp_key = await _uploaded_tmp_key()
    saved = await service.save_image(tmp_key)

    assert await service.save_image(tmp_key) == saved
    assert _exists(saved)


async def test_save_refuses_an_upload_that_does_not_exist() -> None:
    with pytest.raises(service.ImageNotUploadedError) as caught:
        await service.save_image(new_upload_key())

    assert caught.value.code == "image_not_uploaded"
    assert caught.value.status_code == 422


@pytest.mark.parametrize(
    "key",
    ["", "tmp/x.webp", "media/../tmp/a.webp", "products/1.webp", "tmp/" + "a" * 36 + ".webp"],
)
async def test_save_refuses_a_key_of_another_shape(key: str) -> None:
    with pytest.raises(service.InvalidImageKeyError) as caught:
        await service.save_image(key)

    assert caught.value.code == "invalid_image_key"
    assert caught.value.status_code == 422


async def test_save_never_moves_an_object_outside_tmp() -> None:
    bucket = get_settings().s3_bucket
    storage_client().put_object(Bucket=bucket, Key="other/secret.webp", Body=b"x")

    with pytest.raises(service.InvalidImageKeyError):
        await service.save_image("tmp/../other/secret.webp")
    assert _exists("other/secret.webp")


async def test_delete_removes_a_saved_image() -> None:
    saved = await service.save_image(await _uploaded_tmp_key())

    await service.delete_image(saved)

    assert not _exists(saved)
    await service.delete_image(saved)  # already gone: not an error


async def test_delete_refuses_anything_but_a_media_key() -> None:
    tmp_key = await _uploaded_tmp_key()

    for key in (tmp_key, "media/../tmp/x.webp", ""):
        with pytest.raises(service.InvalidImageKeyError):
            await service.delete_image(key)
    assert _exists(tmp_key)


async def test_put_tmp_image_gives_a_key_save_image_accepts() -> None:
    tmp_key = put_tmp_image()

    assert await service.save_image(tmp_key) == _media_key_of(tmp_key)
