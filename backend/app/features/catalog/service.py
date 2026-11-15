"""Catalog queries for the storefront.

A product is shown in the store when it is visible and can be ordered: a `quote`
product always, a `fixed` product only with at least one tier. Soft-deleted rows
(products, tiers, colors) are left out by the global filter in `app.core.db`,
including inside the joins and subqueries below.
"""

from decimal import Decimal
from typing import Any, NamedTuple

from sqlalchemy import (
    ColumnElement,
    ColumnExpressionArgument,
    Select,
    exists,
    func,
    or_,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute, selectinload
from sqlalchemy.sql.selectable import Subquery

from app.core.errors import NotFoundError
from app.features.catalog.models import Category, Product, ProductColor, ProductPriceTier
from app.features.catalog.schemas import Language, ProductFilters, ProductSort
from app.shared.pricing_mode import PricingMode
from app.shared.text_search import LIKE_ESCAPE, contains_pattern


class CategorySummary(NamedTuple):
    category: Category
    product_count: int
    """Products shown in the store only."""
    min_price: Decimal | None


class ProductSummary(NamedTuple):
    product: Product
    price: Decimal | None
    has_colors: bool


async def list_visible_categories(session: AsyncSession) -> list[CategorySummary]:
    """Categories with at least one product in the store, with its count and lowest price."""
    prices = _product_prices()
    stmt = (
        select(Category, func.count(Product.id), func.min(prices.c.price))
        .select_from(Category)
        .join(Product, (Product.category_id == Category.id) & Product.shown_in_store())
        .outerjoin(prices, prices.c.product_id == Product.id)
        .group_by(Category.id)
        .order_by(Category.sort_order, Category.id)
    )
    return [CategorySummary(*row) for row in await session.execute(stmt)]


async def list_visible_products(
    session: AsyncSession, filters: ProductFilters
) -> list[ProductSummary]:
    prices = _product_prices()
    stmt = (
        select(Product, prices.c.price, _has_colors())
        .outerjoin(prices, prices.c.product_id == Product.id)
        .where(Product.shown_in_store(), *_product_conditions(filters, prices.c.price))
        .order_by(*_product_order(filters, prices.c.price))
    )
    return [ProductSummary(*row) for row in await session.execute(stmt)]


async def get_visible_product(session: AsyncSession, product_id: int) -> Product:
    """A product shown in the store, with its category, tiers and colors loaded."""
    stmt = _store_products().where(Product.id == product_id).options(selectinload(Product.category))
    product = await session.scalar(stmt)
    if product is None:
        raise NotFoundError("product_not_found", "Product not found", product_id=product_id)
    return product


async def get_visible_products(session: AsyncSession, product_ids: set[int]) -> dict[int, Product]:
    """Products shown in the store by id, with tiers and colors loaded. Missing ids
    are left out."""
    stmt = _store_products().where(Product.id.in_(product_ids))
    return {product.id: product for product in await session.scalars(stmt)}


def _store_products() -> Select[Product]:
    """Products shown in the store, with what the customer chooses from loaded."""
    return (
        select(Product)
        .where(Product.shown_in_store())
        .options(selectinload(Product.price_tiers), selectinload(Product.colors))
    )


def _product_prices() -> Subquery:
    """The price of each `fixed` product: the lowest price in its quantity table.

    Leftover tiers of a `quote` product are ignored: it has no price.
    """
    return (
        select(
            ProductPriceTier.product_id.label("product_id"),
            func.min(ProductPriceTier.price).label("price"),
        )
        .join(Product, Product.id == ProductPriceTier.product_id)
        .where(Product.pricing_mode == PricingMode.FIXED)
        .group_by(ProductPriceTier.product_id)
        .subquery("product_prices")
    )


def _has_colors() -> ColumnElement[bool]:
    return exists().where(ProductColor.product_id == Product.id).label("has_colors")


def _product_conditions(
    filters: ProductFilters, price: ColumnElement[Decimal]
) -> list[ColumnElement[bool]]:
    """One WHERE condition per filter the customer set."""
    conditions: list[ColumnElement[bool]] = []
    if filters.category_id is not None:
        conditions.append(Product.category_id == filters.category_id)
    if filters.q:
        conditions.append(_name_contains(filters.q))
    if filters.min_price is not None:
        conditions.append(price >= filters.min_price)
    if filters.max_price is not None:
        conditions.append(price <= filters.max_price)
    if filters.pricing_mode is not None:
        conditions.append(Product.pricing_mode == filters.pricing_mode)
    if filters.free_delivery:
        conditions.append(Product.free_delivery.is_(True))
    return conditions


def _name_contains(text: str) -> ColumnElement[bool]:
    pattern = contains_pattern(text)
    return or_(
        Product.name_ar.ilike(pattern, escape=LIKE_ESCAPE),
        Product.name_en.ilike(pattern, escape=LIKE_ESCAPE),
    )


def _product_order(
    filters: ProductFilters, price: ColumnElement[Decimal]
) -> tuple[ColumnExpressionArgument[Any], ...]:
    """ORDER BY for the chosen sort. Quote products (no price) go last both ways."""
    match filters.sort:
        case ProductSort.DEFAULT:
            return (Product.id.desc(),)
        case ProductSort.PRICE_ASC:
            return price.asc().nulls_last(), Product.id.desc()
        case ProductSort.PRICE_DESC:
            return price.desc().nulls_last(), Product.id.desc()
        case ProductSort.NAME:
            # lower(): the database collation is C.UTF-8 (code-point order), where
            # "Zebra" would come before "apple".
            return func.lower(_name_in(filters.lang)), Product.id


def _name_in(lang: Language) -> InstrumentedAttribute[str]:
    return Product.name_ar if lang == Language.AR else Product.name_en
