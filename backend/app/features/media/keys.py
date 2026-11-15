"""Image keys in the bucket, as pure rules without storage.

Every image key is server-generated and has exactly one shape:

    tmp/<uuid4>.webp     a fresh upload, deleted by the bucket after one day
    media/<uuid4>.webp   a saved image, stored in the database and served at /media/...

Anything else (another folder, `..`, a different extension, upper case) is refused, so a
key sent back by the browser can never name another object in the bucket.
"""

import re
import uuid
from typing import NamedTuple

UPLOAD_CONTENT_TYPE = "image/webp"
"""The only type accepted: the dashboard resizes every image to WebP before upload."""

EXTENSION = "webp"
TMP_FOLDER = "tmp"
MEDIA_FOLDER = "media"

MAX_UPLOAD_BYTES = 2 * 1024 * 1024
"""Upper bound of one upload, enforced by S3 in the presigned POST policy. A resized
WebP is a few hundred KB; this only stops an image that was not resized."""

UPLOAD_URL_EXPIRES_SECONDS = 5 * 60

_UUID4 = r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}"
_KEY = re.compile(rf"(?P<folder>{TMP_FOLDER}|{MEDIA_FOLDER})/(?P<name>{_UUID4})\.{EXTENSION}")


class ImageKey(NamedTuple):
    folder: str
    """`tmp` or `media`."""
    name: str
    """The UUID."""

    @property
    def is_saved(self) -> bool:
        return self.folder == MEDIA_FOLDER

    @property
    def media_key(self) -> str:
        """Where this image lives once saved."""
        return f"{MEDIA_FOLDER}/{self.name}.{EXTENSION}"

    @property
    def tmp_key(self) -> str:
        return f"{TMP_FOLDER}/{self.name}.{EXTENSION}"


def new_upload_key() -> str:
    """A fresh, unguessable key in `tmp/` for one upload."""
    return f"{TMP_FOLDER}/{uuid.uuid4()}.{EXTENSION}"


def parse_image_key(key: str) -> ImageKey | None:
    """The key's parts if it has the exact generated shape, otherwise None."""
    match = _KEY.fullmatch(key)
    return None if match is None else ImageKey(match["folder"], match["name"])
