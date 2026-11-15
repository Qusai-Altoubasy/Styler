"""Placing orders, and the manager's order log.

Uses the catalog and settings only through their services.
"""

from collections.abc import Collection, Sequence
from datetime import date, datetime
from decimal import Decimal
from typing import NamedTuple

from sqlalchemy import (
    ColumnElement,
    ColumnExpressionArgument,
    Date,
    cast,
    exists,
    func,
    or_,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.db import soft_delete
from app.core.errors import InvalidRequestError, NotFoundError
from app.features.catalog import service as catalog_service
from app.features.catalog.models import Product
from app.features.orders import pricing
from app.features.orders.enums import OrderStatus
from app.features.orders.item_rules import ItemRejected, freeze_item
from app.features.orders.models import Order, OrderItem
from app.features.orders.schemas import (
    ItemPriceIn,
    MarkFilter,
    OrderCreate,
    OrderFilters,
    OrderItemIn,
    OrderUpdate,
)
from app.features.settings import service as settings_service
from app.shared.governorates import Governorate
from app.shared.ids import MAX_DB_ID
from app.shared.money import MAX_AMOUNT
from app.shared.phone import JORDAN_COUNTRY_CODE, normalize_phone
from app.shared.pricing_mode import PricingMode
from app.shared.text_search import LIKE_ESCAPE, contains_pattern


async def create_order(session: AsyncSession, data: OrderCreate) -> Order:
    """Save a customer order with prices and delivery computed here, never trusted
    from the browser."""
    products = await _load_products(session, data.items)
    items = _freeze_items(data.items, products)
    delivery = await _delivery_fee(session, data.governorate, products.values())
    order = _new_order(data, items, delivery)
    session.add(order)
    await session.commit()
    return order


async def _load_products(session: AsyncSession, items: Sequence[OrderItemIn]) -> dict[int, Product]:
    product_ids = {item.product_id for item in items}
    return await catalog_service.get_visible_products(session, product_ids)


def _freeze_items(items: Sequence[OrderItemIn], products: dict[int, Product]) -> list[OrderItem]:
    """Apply the item rules to every line, reporting which line broke one."""
    frozen: list[OrderItem] = []
    for index, item in enumerate(items):
        try:
            frozen.append(freeze_item(_product_for(item, products), item))
        except ItemRejected as rejected:
            raise InvalidRequestError(
                rejected.code, rejected.message, item_index=index, product_id=item.product_id
            ) from None
    return frozen


def _product_for(item: OrderItemIn, products: dict[int, Product]) -> Product:
    product = products.get(item.product_id)
    if product is None:
        raise ItemRejected("product_unavailable", "This product is no longer available")
    return product


async def _delivery_fee(
    session: AsyncSession, governorate: Governorate, products: Collection[Product]
) -> Decimal:
    zone_fee = await settings_service.delivery_fee_for(session, governorate.zone)
    any_free = any(product.free_delivery for product in products)
    return pricing.delivery_fee(zone_fee, any_free_delivery=any_free)


def _new_order(data: OrderCreate, items: list[OrderItem], delivery: Decimal) -> Order:
    totals = pricing.order_totals(items, delivery)
    _ensure_storable(totals)
    return Order(
        customer_name=data.customer_name,
        phone=data.phone,
        governorate=data.governorate,
        address=data.address,
        delivery_fee=delivery,
        subtotal=totals.subtotal,
        total=totals.total,
        items=items,
    )


def _ensure_storable(totals: pricing.Totals) -> None:
    if totals.total > MAX_AMOUNT:
        raise InvalidRequestError("order_too_large", "The order total is too large")


# --- The manager's order log -------------------------------------------------------

JORDAN_TIME_ZONE = "Asia/Amman"
"""The calendar day of "today" is the one in Jordan, computed by PostgreSQL."""


class OrdersPage(NamedTuple):
    orders: list[Order]
    """With their items loaded."""
    total: int
    """Matching orders across every page."""


class OrderStatsResult(NamedTuple):
    all_orders: int
    today_orders: int
    quote_orders: int
    """Orders with at least one quote item, priced or not."""
    orders_value: Decimal


async def list_orders(session: AsyncSession, filters: OrderFilters) -> OrdersPage:
    """One page of the log, newest first, with the matching count."""
    conditions = _order_conditions(filters)
    total = await _count_orders(session, conditions)
    orders = await _load_page(session, conditions, filters)
    return OrdersPage(orders=orders, total=total)


async def order_stats(session: AsyncSession) -> OrderStatsResult:
    """Counts include cancelled orders; the value leaves them out."""
    not_cancelled = Order.status.is_distinct_from(OrderStatus.CANCELLED)
    stmt = select(
        func.count(Order.id),
        func.count(Order.id).filter(_placed_today()),
        func.count(Order.id).filter(_has_quote_item()),
        func.coalesce(func.sum(Order.total).filter(not_cancelled), pricing.ZERO),
    )
    row = (await session.execute(stmt)).one()
    return OrderStatsResult(*row)


async def get_order(session: AsyncSession, order_id: int) -> Order:
    return await _load_order(session, order_id)


async def update_order(session: AsyncSession, order_id: int, data: OrderUpdate) -> Order:
    """Change the mark, the internal note and the quote prices, then the totals.

    The delivery fee stays as stored on the order. Nothing is sent to the customer.
    """
    order = await _load_order(session, order_id, for_update=True)
    _apply_mark_and_note(order, data)
    if data.item_prices:
        _apply_quote_prices(order, data.item_prices)
        _recalculate_totals(order)
    await session.commit()
    return order


async def delete_order(session: AsyncSession, order_id: int) -> None:
    order = await _load_order(session, order_id, for_update=True)
    for item in order.items:
        await soft_delete(session, item)
    await soft_delete(session, order)
    await session.commit()


def _order_conditions(filters: OrderFilters) -> list[ColumnElement[bool]]:
    conditions: list[ColumnElement[bool]] = []
    match filters.status:
        case MarkFilter.ALL:
            pass
        case MarkFilter.UNMARKED:
            conditions.append(Order.status.is_(None))
        case MarkFilter.DONE:
            conditions.append(Order.status == OrderStatus.DONE)
        case MarkFilter.CANCELLED:
            conditions.append(Order.status == OrderStatus.CANCELLED)
    if filters.q:
        conditions.append(_search(filters.q))
    return conditions


def _search(text: str) -> ColumnElement[bool]:
    """The name always; the phone and the order number when the text is a number.

    The phone is matched as typed by the manager: Arabic digits, spaces, dashes, part
    of the number, or the international form (+962 79...).
    """
    matches: list[ColumnElement[bool]] = [
        Order.customer_name.ilike(contains_pattern(text), escape=LIKE_ESCAPE)
    ]
    digits = _as_digits(text)
    if digits is not None:
        matches.append(
            Order.phone.ilike(contains_pattern(_local_phone(digits)), escape=LIKE_ESCAPE)
        )
        if int(digits) <= MAX_DB_ID:
            matches.append(Order.id == int(digits))
    return or_(*matches)


def _as_digits(text: str) -> str | None:
    """ASCII digits only (a leading + dropped), or None if the text is not a number."""
    digits = normalize_phone(text).removeprefix("+")
    return digits if digits.isascii() and digits.isdigit() else None


def _local_phone(digits: str) -> str:
    """962 79... -> 079..., the form stored on the order."""
    if digits.startswith(JORDAN_COUNTRY_CODE + "7"):
        return "0" + digits.removeprefix(JORDAN_COUNTRY_CODE)
    return digits


def _placed_today() -> ColumnElement[bool]:
    def amman_day(moment: ColumnExpressionArgument[datetime]) -> ColumnElement[date]:
        return cast(func.timezone(JORDAN_TIME_ZONE, moment), Date)

    return amman_day(Order.created_at) == amman_day(func.now())


def _has_quote_item() -> ColumnElement[bool]:
    """The order has a live quote item, whether the manager priced it yet or not."""
    return exists().where(
        OrderItem.order_id == Order.id, OrderItem.pricing_mode == PricingMode.QUOTE
    )


async def _count_orders(session: AsyncSession, conditions: list[ColumnElement[bool]]) -> int:
    return await session.scalar(select(func.count(Order.id)).where(*conditions)) or 0


async def _load_page(
    session: AsyncSession, conditions: list[ColumnElement[bool]], filters: OrderFilters
) -> list[Order]:
    stmt = (
        select(Order)
        .where(*conditions)
        .options(selectinload(Order.items))
        .order_by(Order.id.desc())
        .limit(filters.limit)
        .offset(filters.offset)
    )
    return list(await session.scalars(stmt))


async def _load_order(session: AsyncSession, order_id: int, *, for_update: bool = False) -> Order:
    """The order with its items.

    `for_update` locks the order row until the commit, so two edits of the same order
    (the phone and the laptop, or two quick saves) run one after the other: totals are
    always computed from every price saved so far. The items are loaded by a second
    query that runs after the lock is taken, so they are fresh too. Reads take no lock.
    """
    stmt = select(Order).where(Order.id == order_id).options(selectinload(Order.items))
    if for_update:
        stmt = stmt.with_for_update().execution_options(populate_existing=True)
    order = await session.scalar(stmt)
    if order is None:
        raise NotFoundError("order_not_found", "Order not found", order_id=order_id)
    return order


def _apply_mark_and_note(order: Order, data: OrderUpdate) -> None:
    if data.sets_status:
        order.status = data.status
    if data.sets_internal_note:
        order.internal_note = data.internal_note


def _apply_quote_prices(order: Order, prices: Sequence[ItemPriceIn]) -> None:
    items = {item.id: item for item in order.items}
    for price in prices:
        item = items.get(price.item_id)
        if item is None:
            raise InvalidRequestError(
                "order_item_not_found", "This item is not in the order", item_id=price.item_id
            )
        if item.pricing_mode != PricingMode.QUOTE:
            raise InvalidRequestError(
                "item_price_fixed",
                "Only quote items can be priced; a fixed item keeps its tier price",
                item_id=price.item_id,
            )
        item.unit_price = price.unit_price


def _recalculate_totals(order: Order) -> None:
    """From the items and the delivery fee stored on the order; unpriced items add 0."""
    totals = pricing.order_totals(order.items, order.delivery_fee)
    _ensure_storable(totals)
    order.subtotal = totals.subtotal
    order.total = totals.total
