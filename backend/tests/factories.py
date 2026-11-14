"""Small helpers that add catalog rows for a test. Every row is flushed, not committed."""

from collections.abc import Sequence
from decimal import Decimal
from itertools import count

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.catalog.enums import BrandColor
from app.features.catalog.models import Category, Product, ProductColor, ProductPriceTier
from app.shared.pricing_mode import PricingMode

_names = count(1)


async def add_category(session: AsyncSession, **fields: object) -> Category:
    number = next(_names)
    category = Category(
        **{
            "name_ar": f"تصنيف {number}",
            "name_en": f"Category {number}",
            "color": BrandColor.CYAN,
            **fields,
        }
    )
    session.add(category)
    await session.flush()
    return category


async def add_product(
    session: AsyncSession,
    category: Category | None = None,
    *,
    tiers: Sequence[tuple[int, str]] = (),
    colors: Sequence[tuple[str, str]] = (),
    **fields: object,
) -> Product:
    """A product with its quantity table as (quantity, price) and colors as (name, hex).

    Pricing mode is `fixed` when tiers are given, `quote` otherwise.
    """
    category = category or await add_category(session)
    number = next(_names)
    product = Product(
        **{
            "category_id": category.id,
            "name_ar": f"منتج {number}",
            "name_en": f"Product {number}",
            "pricing_mode": PricingMode.FIXED if tiers else PricingMode.QUOTE,
            **fields,
        }
    )
    session.add(product)
    await session.flush()
    for quantity, price in tiers:
        session.add(
            ProductPriceTier(product_id=product.id, quantity=quantity, price=Decimal(price))
        )
    for index, (name, hex_value) in enumerate(colors):
        session.add(
            ProductColor(
                product_id=product.id, name_ar=name, name_en=name, hex=hex_value, sort_order=index
            )
        )
    await session.flush()
    await session.refresh(product, ["price_tiers", "colors"])
    return product
