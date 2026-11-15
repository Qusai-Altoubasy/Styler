"""Small helpers that add catalog rows for a test. Every row is flushed, not committed."""

from collections.abc import Sequence
from decimal import Decimal
from itertools import count

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.catalog.enums import BrandColor
from app.features.catalog.models import Category, Product, ProductColor, ProductPriceTier
from app.features.orders import pricing
from app.features.orders.models import Order, OrderItem
from app.shared.governorates import Governorate
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


def fixed_item(price: str, item_count: int = 1, **fields: object) -> OrderItem:
    """A frozen `fixed` order line, not yet added to an order."""
    number = next(_names)
    return OrderItem(
        **{
            "product_name_ar": f"منتج {number}",
            "product_name_en": f"Product {number}",
            "pricing_mode": PricingMode.FIXED,
            "quantity": 100,
            "unit_price": Decimal(price),
            "item_count": item_count,
            **fields,
        }
    )


def quote_item(price: str | None = None, item_count: int = 1, **fields: object) -> OrderItem:
    """A frozen `quote` order line, unpriced unless a price is given."""
    number = next(_names)
    return OrderItem(
        **{
            "product_name_ar": f"منتج {number}",
            "product_name_en": f"Product {number}",
            "pricing_mode": PricingMode.QUOTE,
            "unit_price": None if price is None else Decimal(price),
            "item_count": item_count,
            **fields,
        }
    )


async def add_order(
    session: AsyncSession,
    *items: OrderItem,
    delivery_fee: str = "3.000",
    **fields: object,
) -> Order:
    """An order with the given lines (one fixed line by default) and its totals computed.

    Pass `created_at` to place it at a chosen moment, `status` to mark it.
    """
    lines = list(items) or [fixed_item("5.000")]
    delivery = Decimal(delivery_fee)
    totals = pricing.order_totals(lines, delivery)
    order = Order(
        **{
            "customer_name": "Customer",
            "phone": "0791234567",
            "governorate": Governorate.IRBID,
            "address": "Street 1",
            "delivery_fee": delivery,
            "subtotal": totals.subtotal,
            "total": totals.total,
            "items": lines,
            **fields,
        }
    )
    session.add(order)
    await session.flush()
    return order
