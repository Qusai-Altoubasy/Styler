from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.features.settings import service
from app.features.settings.schemas import PublicSettings

router = APIRouter(tags=["settings"])


@router.get("/settings")
async def get_public_settings(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PublicSettings:
    return PublicSettings.from_settings(await service.get_store_settings(session))
