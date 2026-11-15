"""Application settings, read from environment variables only.

No value lives in the code: every setting is required and comes from an env file
passed in by compose (`deploy/.env.dev` locally, the server's env file in production).
A missing setting stops the app at startup with a clear error.
"""

from functools import lru_cache
from typing import Literal

from pydantic import PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    environment: Literal["development", "production"]
    database_url: PostgresDsn
    client_ip_header: str
    """The request header holding the customer's IP, set by the CDN in front of the
    server: `CloudFront-Viewer-Address` in production. Empty when there is no CDN
    (local development): the TCP peer address is used instead."""


@lru_cache
def get_settings() -> Settings:
    return Settings()  # pyright: ignore[reportCallIssue]  (values come from the environment)
