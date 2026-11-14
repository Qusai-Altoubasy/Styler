from decimal import Decimal

import pytest
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.orders.models import Order, OrderItem
from app.features.orders.models.order import FIRST_ORDER_NUMBER
from app.shared.governorates import DeliveryZone, Governorate
from app.shared.pricing_mode import PricingMode


def _order(phone: str = "0791234567") -> Order:
    return Order(
        customer_name="Test",
        phone=phone,
        governorate=Governorate.IRBID,
        address="Street 1",
        delivery_fee=Decimal("3.000"),
        subtotal=Decimal("0.000"),
        total=Decimal("3.000"),
    )


async def test_order_numbers_start_at_1001(db_session: AsyncSession) -> None:
    order = _order()
    db_session.add(order)
    await db_session.flush()

    assert order.id >= FIRST_ORDER_NUMBER


@pytest.mark.parametrize("phone", ["0761234567", "079123456", "+962791234567", "07912345678"])
async def test_order_phone_must_be_a_jordanian_mobile(db_session: AsyncSession, phone: str) -> None:
    # Wrong prefix or too short: the CHECK constraint. Too long: VARCHAR(10) itself.
    with pytest.raises(DBAPIError):
        async with db_session.begin_nested():
            db_session.add(_order(phone))


async def test_fixed_item_must_have_quantity_and_price(db_session: AsyncSession) -> None:
    order = _order()
    db_session.add(order)
    await db_session.flush()

    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            db_session.add(
                OrderItem(
                    order_id=order.id,
                    product_name_ar="ستيكر",
                    product_name_en="Sticker",
                    pricing_mode=PricingMode.FIXED,
                    item_count=1,
                )
            )


async def test_quote_item_can_wait_for_a_price(db_session: AsyncSession) -> None:
    order = _order()
    db_session.add(order)
    await db_session.flush()

    db_session.add(
        OrderItem(
            order_id=order.id,
            product_name_ar="درع",
            product_name_en="Plaque",
            pricing_mode=PricingMode.QUOTE,
            item_count=1,
        )
    )
    await db_session.flush()


def test_only_amman_and_zarqa_are_zone_a() -> None:
    zone_a = {governorate for governorate in Governorate if governorate.zone is DeliveryZone.A}

    assert zone_a == {Governorate.AMMAN, Governorate.ZARQA}
    assert len(Governorate) == 12
