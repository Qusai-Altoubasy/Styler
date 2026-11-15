"""The media tests run against the real MinIO container, in the TEST_S3_BUCKET bucket,
emptied before every test (the shared `empty_bucket` fixture in tests/conftest.py)."""

import pytest


@pytest.fixture(autouse=True)
def _empty_bucket_for_every_media_test(empty_bucket: str) -> None:
    pass
