"""Test uploads into the TEST_S3_BUCKET bucket.

For other features' tests (e.g. saving a product with an image), with `empty_bucket`:
    from tests.media.uploads import put_tmp_image   # key = put_tmp_image()
"""

import httpx

from app.core.config import get_settings
from app.core.storage import storage_client
from app.features.media.keys import UPLOAD_CONTENT_TYPE, new_upload_key

SMALL_WEBP = b"RIFF\x1a\x00\x00\x00WEBPVP8 " + bytes(18)
"""Bytes standing in for an image: the storage checks the declared type and size only."""


def put_tmp_image(content: bytes = SMALL_WEBP) -> str:
    """Puts a small WebP straight into `tmp/` under a fresh key and returns the key, as if
    the dashboard had uploaded it. Ready for `media.service.save_image`."""
    key = new_upload_key()
    storage_client().put_object(
        Bucket=get_settings().s3_bucket, Key=key, Body=content, ContentType=UPLOAD_CONTENT_TYPE
    )
    return key


def browser_url(url: str) -> str:
    """The link is signed for the browser (S3_PUBLIC_ENDPOINT_URL, 127.0.0.1 on the host).

    Inside the container MinIO is at S3_ENDPOINT_URL instead. A POST policy's signature
    covers the policy, not the host, so the same form is valid at either address.
    """
    settings = get_settings()
    return url.replace(settings.s3_public_endpoint_url, settings.s3_endpoint_url, 1)


async def post_upload(
    url: str, fields: dict[str, str], content: bytes, content_type: str = "image/webp"
) -> httpx.Response:
    async with httpx.AsyncClient(timeout=10) as http:
        return await http.post(
            browser_url(url),
            data=fields,
            files={"file": ("image.webp", content, content_type)},
        )
