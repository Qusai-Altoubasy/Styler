"""Image key shapes, without storage."""

import uuid

import pytest

from app.features.media.keys import new_upload_key, parse_image_key

NAME = "3f2b8c1e-5d4a-4e6f-9a7b-1c2d3e4f5a6b"


def test_a_new_upload_key_is_a_fresh_tmp_key() -> None:
    first, second = new_upload_key(), new_upload_key()

    assert first != second
    key = parse_image_key(first)
    assert key is not None
    assert key.folder == "tmp"
    assert not key.is_saved
    assert key.tmp_key == first
    assert key.media_key == f"media/{key.name}.webp"


def test_a_media_key_is_saved_and_keeps_its_name() -> None:
    key = parse_image_key(f"media/{NAME}.webp")

    assert key is not None
    assert key.is_saved
    assert key.media_key == f"media/{NAME}.webp"


@pytest.mark.parametrize(
    "value",
    [
        "",
        NAME,
        f"{NAME}.webp",
        f"other/{NAME}.webp",
        f"/media/{NAME}.webp",
        f"media/{NAME}.png",
        f"media/{NAME}.WEBP",
        f"media/{NAME}",
        f"MEDIA/{NAME}.webp",
        f"media/{NAME.upper()}.webp",
        f"media/{NAME}.webp\n",
        f" media/{NAME}.webp",
        f"media/{NAME}.webp/x",
        f"media/../tmp/{NAME}.webp",
        f"tmp/../media/{NAME}.webp",
        f"media/x/{NAME}.webp",
        f"media/{uuid.uuid1()}.webp",
        "media/../../etc/passwd",
    ],
)
def test_any_other_shape_is_refused(value: str) -> None:
    assert parse_image_key(value) is None
