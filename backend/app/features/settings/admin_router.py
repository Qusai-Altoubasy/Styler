"""`/api/admin/settings`: the settings the manager edits (the password has its own endpoint)."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.features.auth.dependencies import require_admin
from app.features.settings import service
from app.features.settings.schemas import AdminSettings, SettingsUpdate

router = APIRouter(tags=["settings"], dependencies=[Depends(require_admin)])

Session = Annotated[AsyncSession, Depends(get_session)]


@router.get("/settings")
async def get_settings(session: Session) -> AdminSettings:
    return AdminSettings.from_settings(await service.get_store_settings(session))


@router.patch("/settings")
async def update_settings(session: Session, data: SettingsUpdate) -> AdminSettings:
    changes = data.model_dump(exclude_unset=True)
    return AdminSettings.from_settings(await service.update_store_settings(session, changes))
