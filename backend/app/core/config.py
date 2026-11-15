"""Application settings, read from environment variables only.

No value lives in the code: every setting is required and comes from an env file
passed in by compose (`deploy/.env.dev` locally, the server's env file in production).
A missing setting stops the app at startup with a clear error.
"""

from functools import lru_cache
from typing import Literal, Self

from pydantic import Field, PostgresDsn, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Errors name the setting but never echo values: they hold passwords and keys.
    model_config = SettingsConfigDict(extra="ignore", hide_input_in_errors=True)

    environment: Literal["development", "production"]
    database_url: PostgresDsn
    client_ip_header: str
    """The request header holding the customer's IP, set by the CDN in front of the
    server: `CloudFront-Viewer-Address` in production. Empty when there is no CDN
    (local development): the TCP peer address is used instead."""

    s3_bucket: str = Field(min_length=3)
    """The images bucket: `tmp/` for fresh uploads, `media/` for saved images."""
    s3_region: str = Field(min_length=1)
    s3_endpoint_url: str
    """Where the API reaches the storage. Empty in production (real S3); locally the
    MinIO container by its service name (`http://minio:9000`)."""
    s3_public_endpoint_url: str
    """Where the manager's browser sends uploads (the presigned POST link). Empty in
    production (real S3); locally MinIO as seen from the host (`http://127.0.0.1:9000`),
    because the browser cannot resolve the container's service name."""
    s3_access_key_id: str = Field(min_length=1)
    s3_secret_access_key: SecretStr = Field(min_length=1)

    @model_validator(mode="after")
    def _s3_endpoints_together(self) -> Self:
        if bool(self.s3_endpoint_url) != bool(self.s3_public_endpoint_url):
            raise ValueError(
                "S3_ENDPOINT_URL and S3_PUBLIC_ENDPOINT_URL are both empty (real S3) or both set"
            )
        return self

    @property
    def s3_endpoint(self) -> str | None:
        return self.s3_endpoint_url or None

    @property
    def s3_public_endpoint(self) -> str | None:
        return self.s3_public_endpoint_url or None


@lru_cache
def get_settings() -> Settings:
    return Settings()  # pyright: ignore[reportCallIssue]  (values come from the environment)
