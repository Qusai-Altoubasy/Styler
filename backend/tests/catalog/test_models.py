from decimal import Decimal

import pytest
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.catalog.enums import BrandColor
from app.features.catalog.models import Category, Product, ProductColor, ProductPriceTier
from app.shared.pricing_mode import PricingMode


async def _add_category(session: AsyncSession, name: str = "ملابس مطبوعة") -> Category:
    category = Category(name_ar=name, name_en=f"{name} (en)", color=BrandColor.CYAN)
    session.add(category)
    await session.flush()
    return category


async def _add_product(session: AsyncSession) -> Product:
    category = await _add_category(session)
    product = Product(
        category_id=category.id,
        name_ar="تيشيرت",
        name_en="T-shirt",
        pricing_mode=PricingMode.FIXED,
    )
    session.add(product)
    await session.flush()
    return product


async def test_category_name_must_be_unique_among_live_rows(db_session: AsyncSession) -> None:
    existing = await _add_category(db_session)

    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            db_session.add(
                Category(name_ar=existing.name_ar, name_en="Other", color=BrandColor.BLACK)
            )


async def test_category_name_can_be_reused_after_soft_delete(db_session: AsyncSession) -> None:
    existing = await _add_category(db_session)
    existing.deleted_at = func.now()
    await db_session.flush()

    db_session.add(
        Category(name_ar=existing.name_ar, name_en=existing.name_en, color=BrandColor.CYAN)
    )
    await db_session.flush()


async def test_price_tier_quantity_must_be_positive(db_session: AsyncSession) -> None:
    product = await _add_product(db_session)

    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            db_session.add(ProductPriceTier(product_id=product.id, quantity=0, price=Decimal(1)))


async def test_color_hex_must_be_lowercase_rrggbb(db_session: AsyncSession) -> None:
    product = await _add_product(db_session)

    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            db_session.add(
                ProductColor(product_id=product.id, name_ar="أحمر", name_en="Red", hex="#FF0000")
            )


async def test_category_names_clash_ignoring_case_and_spaces(db_session: AsyncSession) -> None:
    db_session.add(Category(name_ar="أكواب", name_en="Mugs", color=BrandColor.CYAN))
    await db_session.flush()

    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            db_session.add(Category(name_ar="مطرات", name_en=" mugs ", color=BrandColor.CYAN))


async def test_same_quantity_is_allowed_with_a_different_note(db_session: AsyncSession) -> None:
    product = await _add_product(db_session)

    db_session.add_all(
        [
            ProductPriceTier(product_id=product.id, quantity=250, price=Decimal(7), note_en="4 cm"),
            ProductPriceTier(product_id=product.id, quantity=250, price=Decimal(9), note_en="6 cm"),
        ]
    )
    await db_session.flush()


async def test_exact_duplicate_tier_is_refused(db_session: AsyncSession) -> None:
    product = await _add_product(db_session)
    db_session.add(ProductPriceTier(product_id=product.id, quantity=100, price=Decimal(5)))
    await db_session.flush()

    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            db_session.add(ProductPriceTier(product_id=product.id, quantity=100, price=Decimal(6)))
