"""What a customer may order for one product: pure rules, no database.

Each check raises `ItemRejected`; the service adds which line of the order it was.
"""

from app.features.catalog.models import Product, ProductColor, ProductPriceTier
from app.features.orders.models import OrderItem
from app.features.orders.schemas import OrderItemIn
from app.shared.pricing_mode import PricingMode


class ItemRejected(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def freeze_item(product: Product, item: OrderItemIn) -> OrderItem:
    """A frozen copy of what the customer chose, priced from the live product."""
    tier = chosen_tier(product, item)
    color = chosen_color(product, item)
    return OrderItem(
        product_id=product.id,
        product_name_ar=product.name_ar,
        product_name_en=product.name_en,
        pricing_mode=product.pricing_mode,
        item_count=item.item_count,
        quantity=tier.quantity if tier else item.approx_quantity,
        tier_note_ar=tier.note_ar if tier else None,
        tier_note_en=tier.note_en if tier else None,
        unit_price=tier.price if tier else None,
        color_name_ar=color.name_ar if color else None,
        color_name_en=color.name_en if color else None,
        color_hex=color.hex if color else None,
    )


def chosen_tier(product: Product, item: OrderItemIn) -> ProductPriceTier | None:
    """The tier of a `fixed` product; None for a `quote` product, which has no tiers."""
    match product.pricing_mode:
        case PricingMode.FIXED:
            return _fixed_tier(product, item)
        case PricingMode.QUOTE:
            _ensure_no_tier(item)
            return None


def chosen_color(product: Product, item: OrderItemIn) -> ProductColor | None:
    """Required when the product has colors, not allowed otherwise."""
    if not product.colors:
        _ensure_no_color(item)
        return None
    return _picked_color(product, item)


def _fixed_tier(product: Product, item: OrderItemIn) -> ProductPriceTier:
    if item.approx_quantity is not None:
        raise ItemRejected(
            "approx_quantity_not_allowed",
            "Fixed-price products take a tier, not an approximate quantity",
        )
    if item.tier_id is None:
        raise ItemRejected("tier_required", "Choose a quantity")
    tier = next((tier for tier in product.price_tiers if tier.id == item.tier_id), None)
    if tier is None:
        raise ItemRejected("tier_not_found", "This quantity is no longer available")
    return tier


def _picked_color(product: Product, item: OrderItemIn) -> ProductColor:
    if item.color_id is None:
        raise ItemRejected("color_required", "Choose a color")
    color = next((color for color in product.colors if color.id == item.color_id), None)
    if color is None:
        raise ItemRejected("color_not_found", "This color is no longer available")
    return color


def _ensure_no_tier(item: OrderItemIn) -> None:
    if item.tier_id is not None:
        raise ItemRejected("tier_not_allowed", "Quote products have no quantity table")


def _ensure_no_color(item: OrderItemIn) -> None:
    if item.color_id is not None:
        raise ItemRejected("color_not_allowed", "This product is not available in colors")
