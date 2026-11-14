"""Turning a stored image key into the link the browser loads.

Images are stored as their S3 key (`media/<uuid>.webp`). Both CloudFront
distributions serve `/media/*` on their own domain, so the link is a plain path;
in local development the frontend dev server proxies `/media/*` to MinIO.
"""


def image_url(image_key: str | None) -> str | None:
    return None if image_key is None else f"/{image_key}"
