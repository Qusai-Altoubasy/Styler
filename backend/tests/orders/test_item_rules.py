"""What a customer may order for one product, checked without the database."""

from decimal import Decimal

import pytest

from app.features.catalog.models import Product, ProductColor, ProductPriceTier
from app.features.orders.item_rules import ItemRejected, freeze_item
from app.features.orders.schemas import OrderItemIn
from app.shared.pricing_mode import PricingMode

TIER_ID, COLOR_ID = 10, 20


def _product(mode: PricingMode = PricingMode.FIXED, *, with_color: bool = False) -> Product:
    product = Product(id=1, name_ar="كوب", name_en="Mug", pricing_mode=mode)
    product.price_tiers = (
        [ProductPriceTier(id=TIER_ID, quantity=250, price=Decimal("7.000"), note_en="4 cm")]
        if mode == PricingMode.FIXED
        else []
    )
    product.colors = (
        [ProductColor(id=COLOR_ID, name_ar="أحمر", name_en="Red", hex="#ff0000")]
        if with_color
        else []
    )
    return product


def _rejected_code(product: Product, **item: int) -> str:
    with pytest.raises(ItemRejected) as rejected:
        freeze_item(product, OrderItemIn(product_id=1, **item))
    return rejected.value.code


def test_fixed_item_copies_the_tier_price_and_note() -> None:
    item = freeze_item(_product(), OrderItemIn(product_id=1, tier_id=TIER_ID, item_count=3))

    assert (item.quantity, item.unit_price, item.tier_note_en) == (250, Decimal("7.000"), "4 cm")
    assert (item.product_name_en, item.item_count) == ("Mug", 3)


def test_quote_item_keeps_the_approximate_quantity_and_has_no_price() -> None:
    product = _product(PricingMode.QUOTE)

    item = freeze_item(product, OrderItemIn(product_id=1, approx_quantity=300))

    assert (item.quantity, item.unit_price) == (300, None)


def test_color_is_copied_onto_the_item() -> None:
    product = _product(with_color=True)

    item = freeze_item(product, OrderItemIn(product_id=1, tier_id=TIER_ID, color_id=COLOR_ID))

    assert (item.color_name_en, item.color_hex) == ("Red", "#ff0000")


@pytest.mark.parametrize(
    ("mode", "with_color", "item", "code"),
    [
        (PricingMode.FIXED, False, {}, "tier_required"),
        (PricingMode.FIXED, False, {"tier_id": 999}, "tier_not_found"),
        (
            PricingMode.FIXED,
            False,
            {"tier_id": TIER_ID, "approx_quantity": 5},
            "approx_quantity_not_allowed",
        ),
        (PricingMode.QUOTE, False, {"tier_id": TIER_ID}, "tier_not_allowed"),
        (PricingMode.QUOTE, True, {}, "color_required"),
        (PricingMode.QUOTE, True, {"color_id": 999}, "color_not_found"),
        (PricingMode.QUOTE, False, {"color_id": COLOR_ID}, "color_not_allowed"),
    ],
)
def test_broken_rules_are_rejected_with_their_code(
    mode: PricingMode, with_color: bool, item: dict[str, int], code: str
) -> None:
    assert _rejected_code(_product(mode, with_color=with_color), **item) == code
