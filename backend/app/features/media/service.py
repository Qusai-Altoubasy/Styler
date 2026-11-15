"""Image upload links, and moving uploads into `media/` when a product or category is saved.

The flow, for the catalog's admin endpoints:

1. The dashboard asks for an upload link (`create_upload_url`) and posts the resized
   WebP straight to the bucket, under `tmp/<uuid>.webp`.
2. It sends that key with the product or category. Before committing, the catalog calls
   `save_image(key)`, which moves the object to `media/<uuid>.webp` and returns the key to
   store. A key already in `media/` (an edit that keeps the image) comes back unchanged.
3. When an image is replaced or removed, the catalog calls `delete_image(old_key)` after
   its commit. Uploads that were never saved are deleted by the bucket after one day.

Access denied by the storage is never read as "no such image": it means the server's key
lacks a permission (see `REQUIRED_PERMISSIONS`), and it fails loudly as
`StorageMisconfiguredError` with a log line naming what is missing.
"""

import asyncio
import logging
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any, NamedTuple

from botocore.exceptions import ClientError

from app.core.config import get_settings
from app.core.errors import AppError, InvalidRequestError
from app.core.storage import is_access_denied, is_missing, storage_client, upload_signing_client
from app.features.media.keys import (
    MAX_UPLOAD_BYTES,
    UPLOAD_CONTENT_TYPE,
    UPLOAD_URL_EXPIRES_SECONDS,
    ImageKey,
    new_upload_key,
    parse_image_key,
)

logger = logging.getLogger(__name__)

REQUIRED_PERMISSIONS = (
    "s3:ListBucket on the bucket, and s3:GetObject, s3:PutObject and s3:DeleteObject on "
    "tmp/* and media/*. Without s3:ListBucket, S3 answers 403 AccessDenied instead of "
    "404 for an object that does not exist"
)

SAVED_IMAGE_CACHE_CONTROL = "public, max-age=31536000, immutable"
"""A saved image never changes (a new image gets a new key), so the CDN and browsers
may keep it for a year."""


class InvalidImageKeyError(InvalidRequestError):
    def __init__(self) -> None:
        super().__init__("invalid_image_key", "Unknown image key")


class ImageNotUploadedError(InvalidRequestError):
    """The upload never finished, or it was not saved within a day and was deleted."""

    def __init__(self) -> None:
        super().__init__("image_not_uploaded", "The image was not uploaded, upload it again")


class StorageMisconfiguredError(AppError):
    """The storage refused the server's own key: a deployment fault, not the manager's.

    500, not 503: retrying does not help until the key's permissions are fixed. The
    details are in the server log, not in the response.
    """

    status_code = 500

    def __init__(self) -> None:
        super().__init__("storage_misconfigured", "Image storage is not set up correctly")


class UploadUrl(NamedTuple):
    url: str
    """Where the browser posts the form."""
    fields: dict[str, str]
    """Form fields to send as they are, before the file."""
    key: str
    """The key to send back with the product or category."""


async def create_upload_url(content_type: str) -> UploadUrl:
    """A presigned POST for one image, valid for 5 minutes.

    The policy fixes the key, the content type and the size range, so the browser can
    upload this one object and nothing else.
    """
    key = new_upload_key()
    presigned: dict[str, Any] = upload_signing_client().generate_presigned_post(
        Bucket=get_settings().s3_bucket,
        Key=key,
        Fields={"Content-Type": content_type},
        Conditions=[
            {"Content-Type": content_type},
            ["content-length-range", 1, MAX_UPLOAD_BYTES],
        ],
        ExpiresIn=UPLOAD_URL_EXPIRES_SECONDS,
    )
    fields = {name: str(value) for name, value in presigned["fields"].items()}
    return UploadUrl(url=presigned["url"], fields=fields, key=key)


async def save_image(image_key: str) -> str:
    """The `media/` key to store for an image the browser sent back.

    Moves a `tmp/` upload to `media/`; a `media/` key is returned unchanged without
    touching the storage. Call it before committing the row that stores the key.

    Raises `InvalidImageKeyError` for any key not of the generated shape, and
    `ImageNotUploadedError` when the `tmp/` object does not exist.
    """
    key = _parse(image_key)
    if key.is_saved:
        return key.media_key
    await _move_to_media(key)
    return key.media_key


async def delete_image(image_key: str) -> None:
    """Deletes a saved image. Call it after the commit that stopped using it.

    Deleting an image that is already gone is not an error.
    """
    key = _parse(image_key)
    if not key.is_saved:
        raise InvalidImageKeyError()
    bucket = get_settings().s3_bucket
    with _denied_means_misconfigured("DeleteObject", bucket, key.media_key):
        await asyncio.to_thread(storage_client().delete_object, Bucket=bucket, Key=key.media_key)


def _parse(image_key: str) -> ImageKey:
    key = parse_image_key(image_key)
    if key is None:
        raise InvalidImageKeyError()
    return key


async def _move_to_media(key: ImageKey) -> None:
    bucket = get_settings().s3_bucket
    client = storage_client()
    try:
        with _denied_means_misconfigured("CopyObject", bucket, key.tmp_key):
            await asyncio.to_thread(
                client.copy_object,
                Bucket=bucket,
                Key=key.media_key,
                CopySource={"Bucket": bucket, "Key": key.tmp_key},
                MetadataDirective="REPLACE",
                ContentType=UPLOAD_CONTENT_TYPE,
                CacheControl=SAVED_IMAGE_CACHE_CONTROL,
            )
    except ClientError as error:
        if not is_missing(error):
            raise
        # A retried save whose first attempt already moved the image (and then failed to
        # commit) finds tmp/ empty but media/ filled: that is a success.
        if await _exists(bucket, key.media_key):
            return
        raise ImageNotUploadedError() from error
    with _denied_means_misconfigured("DeleteObject", bucket, key.tmp_key):
        await asyncio.to_thread(client.delete_object, Bucket=bucket, Key=key.tmp_key)


async def _exists(bucket: str, key: str) -> bool:
    try:
        with _denied_means_misconfigured("HeadObject", bucket, key):
            await asyncio.to_thread(storage_client().head_object, Bucket=bucket, Key=key)
    except ClientError as error:
        if is_missing(error):
            return False
        raise
    return True


@contextmanager
def _denied_means_misconfigured(operation: str, bucket: str, key: str) -> Iterator[None]:
    """Turns the storage's access denied into a logged `StorageMisconfiguredError`.

    With the permissions in `REQUIRED_PERMISSIONS`, S3 answers 404 for a missing object,
    so a 403 here always means the key is missing a permission, never a missing image.
    """
    try:
        yield
    except ClientError as error:
        if not is_access_denied(error):
            raise
        logger.error(
            "Image storage denied %s on s3://%s/%s (%s). The server's key needs %s.",
            operation,
            bucket,
            key,
            error.response.get("Error", {}).get("Code"),
            REQUIRED_PERMISSIONS,
        )
        raise StorageMisconfiguredError() from error
