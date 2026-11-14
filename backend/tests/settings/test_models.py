from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.settings.models import Setting
from app.features.settings.models.setting import SETTINGS_ROW_ID


def _settings() -> Setting:
    return Setting(
        zone_a_delivery_fee=Decimal("2.000"),
        zone_b_delivery_fee=Decimal("3.000"),
        whatsapp_number="0790087017",
    )


async def test_settings_row_gets_id_1_without_passing_it(db_session: AsyncSession) -> None:
    settings = _settings()
    db_session.add(settings)
    await db_session.flush()

    assert settings.id == SETTINGS_ROW_ID


async def test_a_second_settings_row_is_refused(db_session: AsyncSession) -> None:
    db_session.add(_settings())
    await db_session.flush()

    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            db_session.add(_settings())
