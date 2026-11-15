"""The upload link request and answer."""

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict

from app.features.media.keys import MAX_UPLOAD_BYTES, UPLOAD_URL_EXPIRES_SECONDS
from app.features.media.service import UploadUrl


class UploadUrlIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content_type: Literal["image/webp"]
    """What the browser will upload. Only WebP: the dashboard converts every image."""


class UploadUrlOut(BaseModel):
    """A presigned POST: send `fields` as form fields, then the image as `file`, to `url`."""

    url: str
    fields: dict[str, str]
    key: str
    """Send this back as the product's or category's image key."""
    max_bytes: int
    expires_in_seconds: int

    @classmethod
    def from_upload_url(cls, upload: UploadUrl) -> Self:
        return cls(
            url=upload.url,
            fields=upload.fields,
            key=upload.key,
            max_bytes=MAX_UPLOAD_BYTES,
            expires_in_seconds=UPLOAD_URL_EXPIRES_SECONDS,
        )
