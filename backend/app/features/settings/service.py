"""The store settings: the single row seeded by migration 0009."""

from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.settings.models import Setting
from app.features.settings.models.setting import SETTINGS_ROW_ID
from app.shared.governorates import DeliveryZone

EDITABLE_FIELDS = frozenset(
    {
        "zone_a_delivery_fee",
        "zone_b_delivery_fee",
        "whatsapp_number",
        "instagram_url",
        "facebook_url",
    }
)


async def get_store_settings(session: AsyncSession) -> Setting:
    settings = await session.get(Setting, SETTINGS_ROW_ID)
    if settings is None:  # only if migration 0009 did not run
        raise RuntimeError("The settings row is missing; run `alembic upgrade head`")
    return settings


async def delivery_fee_for(session: AsyncSession, zone: DeliveryZone) -> Decimal:
    settings = await get_store_settings(session)
    return settings.delivery_fee_for(zone)


async def get_admin_password_hash(session: AsyncSession) -> str | None:
    settings = await get_store_settings(session)
    return settings.admin_password_hash


async def set_admin_password_hash(session: AsyncSession, password_hash: str) -> None:
    """Part of the caller's unit of work: flushed, not committed."""
    settings = await get_store_settings(session)
    settings.admin_password_hash = password_hash
    await session.flush()


async def update_store_settings(session: AsyncSession, changes: dict[str, Any]) -> Setting:
    """Applies the editable fields in `changes` (already validated) and commits."""
    settings = await get_store_settings(session)
    for field in EDITABLE_FIELDS & changes.keys():
        setattr(settings, field, changes[field])
    await session.commit()
    await session.refresh(settings)
    return settings
