"""The store settings: the single row seeded by migration 0009."""

from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.settings.models import Setting
from app.features.settings.models.setting import SETTINGS_ROW_ID
from app.shared.governorates import DeliveryZone


async def get_store_settings(session: AsyncSession) -> Setting:
    settings = await session.get(Setting, SETTINGS_ROW_ID)
    if settings is None:  # only if migration 0009 did not run
        raise RuntimeError("The settings row is missing; run `alembic upgrade head`")
    return settings


async def delivery_fee_for(session: AsyncSession, zone: DeliveryZone) -> Decimal:
    settings = await get_store_settings(session)
    return settings.delivery_fee_for(zone)
