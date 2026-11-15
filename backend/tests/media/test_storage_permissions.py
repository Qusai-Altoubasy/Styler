"""The server key's permissions, and what happens when one is missing.

Production: without `s3:ListBucket`, S3 answers 403 AccessDenied (not 404) for an object
that does not exist. MinIO does not reproduce that: it answers 404 either way (checked with
a key lacking ListBucket below). So the real MinIO tests prove that the documented policy is
enough for the whole flow, and stubbed 403 answers prove that a denial fails loudly as
`storage_misconfigured` instead of a 500 without a code or a false `image_not_uploaded`.
"""

import json
import logging
from collections.abc import Callable
from typing import Any

import boto3
import pytest
from botocore.config import Config
from botocore.exceptions import ClientError

from app.core.config import get_settings
from app.core.storage import is_access_denied, is_missing
from app.features.media import service
from app.features.media.keys import new_upload_key, parse_image_key
from tests.media.uploads import put_tmp_image


def server_key_policy(bucket: str, *, list_bucket: bool = True) -> str:
    """The IAM policy the server's key needs (backend/README.md, Images)."""
    statements: list[dict[str, Any]] = [
        {
            "Effect": "Allow",
            "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
            "Resource": [f"arn:aws:s3:::{bucket}/tmp/*", f"arn:aws:s3:::{bucket}/media/*"],
        }
    ]
    if list_bucket:
        statements.append(
            {"Effect": "Allow", "Action": ["s3:ListBucket"], "Resource": [f"arn:aws:s3:::{bucket}"]}
        )
    return json.dumps({"Version": "2012-10-17", "Statement": statements})


def _restricted_client(bucket: str, *, list_bucket: bool) -> Any:
    """An S3 client on MinIO holding only `server_key_policy`, through temporary
    credentials (MinIO's STS AssumeRole with an inline policy)."""
    settings = get_settings()
    config = Config(signature_version="s3v4", s3={"addressing_style": "path"})
    sts: Any = boto3.client(
        "sts",
        region_name=settings.s3_region,
        endpoint_url=settings.s3_endpoint,
        aws_access_key_id=settings.s3_access_key_id,
        aws_secret_access_key=settings.s3_secret_access_key.get_secret_value(),
        config=config,
    )
    credentials = sts.assume_role(
        RoleArn="arn:aws:iam::000000000000:role/server-key",
        RoleSessionName="media-tests",
        Policy=server_key_policy(bucket, list_bucket=list_bucket),
        DurationSeconds=900,
    )["Credentials"]
    return boto3.client(
        "s3",
        aws_access_key_id=credentials["AccessKeyId"],
        aws_secret_access_key=credentials["SecretAccessKey"],
        aws_session_token=credentials["SessionToken"],
        region_name=settings.s3_region,
        endpoint_url=settings.s3_endpoint,
        config=config,
    )


UseServerKey = Callable[..., Any]


@pytest.fixture
def use_server_key(monkeypatch: pytest.MonkeyPatch, empty_bucket: str) -> UseServerKey:
    """Makes the media service use a key holding only the production policy."""

    def use(*, list_bucket: bool = True) -> Any:
        client = _restricted_client(empty_bucket, list_bucket=list_bucket)
        monkeypatch.setattr(service, "storage_client", lambda: client)
        return client

    return use


def _media_key_of(tmp_key: str) -> str:
    key = parse_image_key(tmp_key)
    assert key is not None
    return key.media_key


# --- the documented policy on MinIO ---


async def test_the_policy_is_enough_for_save_retry_and_delete(
    use_server_key: UseServerKey,
) -> None:
    use_server_key()
    tmp_key = put_tmp_image()

    saved = await service.save_image(tmp_key)
    assert saved == _media_key_of(tmp_key)
    assert await service.save_image(tmp_key) == saved  # the retry path (HEAD on media/)
    await service.delete_image(saved)


async def test_with_list_bucket_a_missing_upload_is_image_not_uploaded(
    use_server_key: UseServerKey,
) -> None:
    use_server_key()

    with pytest.raises(service.ImageNotUploadedError):
        await service.save_image(new_upload_key())


async def test_the_policy_is_enforced_by_minio(
    use_server_key: UseServerKey, empty_bucket: str
) -> None:
    client = use_server_key(list_bucket=False)

    with pytest.raises(ClientError) as listing:
        client.list_objects_v2(Bucket=empty_bucket)
    assert is_access_denied(listing.value)
    with pytest.raises(ClientError) as elsewhere:
        client.put_object(Bucket=empty_bucket, Key="other/x.webp", Body=b"x")
    assert is_access_denied(elsewhere.value)
    # Unlike S3, MinIO still answers 404 for a missing object without ListBucket, which
    # is why the 403 case is tested with stubbed answers below.
    with pytest.raises(ClientError) as missing:
        client.head_object(Bucket=empty_bucket, Key=new_upload_key())
    assert is_missing(missing.value)


# --- S3's 403 answers, stubbed ---


def _error(code: str, status: int, operation: str) -> ClientError:
    response: Any = {
        "Error": {"Code": code, "Message": code},
        "ResponseMetadata": {"HTTPStatusCode": status},
    }
    return ClientError(response, operation)


class _StubStorage:
    """Answers each call with the given error, like S3 would."""

    def __init__(self, **errors: ClientError) -> None:
        self.errors = errors

    def _answer(self, operation: str) -> dict[str, Any]:
        if operation in self.errors:
            raise self.errors[operation]
        return {}

    def copy_object(self, **_: Any) -> dict[str, Any]:
        return self._answer("copy_object")

    def head_object(self, **_: Any) -> dict[str, Any]:
        return self._answer("head_object")

    def delete_object(self, **_: Any) -> dict[str, Any]:
        return self._answer("delete_object")


def _stub(monkeypatch: pytest.MonkeyPatch, storage: _StubStorage) -> None:
    monkeypatch.setattr(service, "storage_client", lambda: storage)


def _assert_logged_permissions(caplog: pytest.LogCaptureFixture, operation: str) -> None:
    errors = [r for r in caplog.records if r.levelno == logging.ERROR]
    assert len(errors) == 1
    message = errors[0].getMessage()
    assert operation in message
    assert "s3:ListBucket" in message


async def test_a_denied_copy_is_storage_misconfigured_not_image_not_uploaded(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """What S3 answers for an expired upload when the key lacks s3:ListBucket."""
    _stub(monkeypatch, _StubStorage(copy_object=_error("AccessDenied", 403, "CopyObject")))

    with pytest.raises(service.StorageMisconfiguredError) as caught:
        await service.save_image(new_upload_key())

    assert caught.value.code == "storage_misconfigured"
    assert caught.value.status_code == 500
    _assert_logged_permissions(caplog, "CopyObject")


async def test_a_denied_head_on_the_retry_path_is_storage_misconfigured(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    _stub(
        monkeypatch,
        _StubStorage(
            copy_object=_error("NoSuchKey", 404, "CopyObject"),
            head_object=_error("403", 403, "HeadObject"),
        ),
    )

    with pytest.raises(service.StorageMisconfiguredError):
        await service.save_image(new_upload_key())
    _assert_logged_permissions(caplog, "HeadObject")


async def test_a_denied_delete_is_storage_misconfigured(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    _stub(monkeypatch, _StubStorage(delete_object=_error("AccessDenied", 403, "DeleteObject")))

    with pytest.raises(service.StorageMisconfiguredError):
        await service.delete_image(_media_key_of(new_upload_key()))
    _assert_logged_permissions(caplog, "DeleteObject")


async def test_other_storage_errors_are_not_disguised(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub(monkeypatch, _StubStorage(copy_object=_error("SlowDown", 503, "CopyObject")))

    with pytest.raises(ClientError):
        await service.save_image(new_upload_key())


@pytest.mark.parametrize(
    ("code", "missing", "denied"),
    [
        ("NoSuchKey", True, False),
        ("404", True, False),
        ("NotFound", True, False),
        ("AccessDenied", False, True),
        ("403", False, True),
        ("Forbidden", False, True),
        ("SlowDown", False, False),
    ],
)
def test_error_codes_are_classified(code: str, missing: bool, denied: bool) -> None:
    error = _error(code, 0, "Any")

    assert is_missing(error) is missing
    assert is_access_denied(error) is denied
