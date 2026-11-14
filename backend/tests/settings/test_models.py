from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.settings.models import Setting
from app.features.settings.models.setting import SETTINGS_ROW_ID


async def test_migrations_seed_the_settings_row(db_session: AsyncSession) -> None:
    settings = (await db_session.scalars(select(Setting))).one()

    assert settings.id == SETTINGS_ROW_ID
    assert settings.zone_a_delivery_fee == Decimal("2.000")
    assert settings.zone_b_delivery_fee == Decimal("3.000")
    assert settings.whatsapp_number == "0790087017"
    assert settings.admin_password_hash is None


async def test_a_second_settings_row_is_refused(db_session: AsyncSession) -> None:
    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            db_session.add(
                Setting(
                    zone_a_delivery_fee=Decimal("2.000"),
                    zone_b_delivery_fee=Decimal("3.000"),
                    whatsapp_number="0790087017",
                )
            )
