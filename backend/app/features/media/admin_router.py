"""`/api/admin/media`: upload links for product and category images."""

from fastapi import APIRouter, Depends

from app.features.auth.dependencies import require_admin
from app.features.media import service
from app.features.media.schemas import UploadUrlIn, UploadUrlOut

router = APIRouter(prefix="/media", tags=["media"], dependencies=[Depends(require_admin)])


@router.post("/upload-url")
async def create_upload_url(data: UploadUrlIn) -> UploadUrlOut:
    """A link the dashboard uploads one image to, straight to the bucket (5 minutes)."""
    return UploadUrlOut.from_upload_url(await service.create_upload_url(data.content_type))
