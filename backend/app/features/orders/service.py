"""Placing orders. Uses the catalog and settings only through their services."""

from collections.abc import Collection, Sequence
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import InvalidRequestError
from app.features.catalog import service as catalog_service
from app.features.catalog.models import Product
from app.features.orders import pricing
from app.features.orders.item_rules import ItemRejected, freeze_item
from app.features.orders.models import Order, OrderItem
from app.features.orders.schemas import OrderCreate, OrderItemIn
from app.features.settings import service as settings_service
from app.shared.governorates import Governorate


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
    if totals.total > pricing.MAX_AMOUNT:
        raise InvalidRequestError("order_too_large", "The order total is too large")
