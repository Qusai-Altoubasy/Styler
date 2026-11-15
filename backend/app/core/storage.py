"""S3 clients for the images bucket (MinIO in local development).

boto3 is synchronous: network calls go through `asyncio.to_thread` in the services, so
they never block the event loop. Clients are thread-safe and created once.

Two clients, because the API and the manager's browser may reach the storage at
different addresses:

- `storage_client()`: the API's own calls (copy, delete), at `S3_ENDPOINT_URL`.
- `upload_signing_client()`: only signs presigned POST links, which the browser uses, so
  the link carries `S3_PUBLIC_ENDPOINT_URL`. Signing makes no network call.

In production both endpoints are empty and both clients talk to real S3.
"""

from functools import lru_cache
from typing import TYPE_CHECKING

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.core.config import get_settings

if TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client


def _client(endpoint_url: str | None) -> S3Client:
    settings = get_settings()
    return boto3.client(
        "s3",
        region_name=settings.s3_region,
        endpoint_url=endpoint_url,
        aws_access_key_id=settings.s3_access_key_id,
        aws_secret_access_key=settings.s3_secret_access_key.get_secret_value(),
        config=Config(
            signature_version="s3v4",
            # MinIO serves buckets by path (host/bucket/key); real S3 by host name.
            s3={"addressing_style": "path" if endpoint_url else "virtual"},
            connect_timeout=5,
            read_timeout=30,
            retries={"max_attempts": 3, "mode": "standard"},
        ),
    )


@lru_cache
def storage_client() -> S3Client:
    return _client(get_settings().s3_endpoint)


@lru_cache
def upload_signing_client() -> S3Client:
    return _client(get_settings().s3_public_endpoint)


def _error_code(error: ClientError) -> str | None:
    return error.response.get("Error", {}).get("Code")


def is_missing(error: ClientError) -> bool:
    """The object does not exist (404). HEAD answers carry the bare status as the code."""
    return _error_code(error) in {"NoSuchKey", "NotFound", "404"}


def is_access_denied(error: ClientError) -> bool:
    """The key may not do this (403). On S3 this also covers a missing object when the key
    lacks `s3:ListBucket`, so it can never be read as "missing"."""
    return _error_code(error) in {"AccessDenied", "Forbidden", "403"}
