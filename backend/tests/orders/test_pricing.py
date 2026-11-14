"""Totals and delivery rules, without the database."""

from decimal import Decimal

from app.features.orders import pricing
from app.features.orders.pricing import Line

ZONE_FEE = Decimal("3.000")


def test_fixed_order_sums_lines_and_adds_delivery() -> None:
    lines = [Line(Decimal("7.000"), 2), Line(Decimal("1.500"), 1)]

    totals = pricing.order_totals(lines, ZONE_FEE)

    assert totals.subtotal == Decimal("15.500")
    assert totals.total == Decimal("18.500")
    assert pricing.awaiting_quote(lines) is False


def test_quote_only_order_totals_delivery_and_awaits_a_price() -> None:
    lines = [Line(None, 3)]

    totals = pricing.order_totals(lines, ZONE_FEE)

    assert totals.subtotal == Decimal("0.000")
    assert totals.total == ZONE_FEE
    assert pricing.awaiting_quote(lines) is True


def test_mixed_order_counts_only_the_priced_lines() -> None:
    lines = [Line(Decimal("5.000"), 2), Line(None, 1)]

    totals = pricing.order_totals(lines, ZONE_FEE)

    assert totals.subtotal == Decimal("10.000")
    assert totals.total == Decimal("13.000")
    assert pricing.awaiting_quote(lines) is True


def test_pricing_a_quote_line_adds_it_to_the_totals() -> None:
    lines = [Line(Decimal("5.000"), 2), Line(Decimal("4.250"), 2)]

    totals = pricing.order_totals(lines, ZONE_FEE)

    assert totals.subtotal == Decimal("18.500")
    assert pricing.awaiting_quote(lines) is False


def test_free_delivery_product_makes_delivery_free() -> None:
    assert pricing.delivery_fee(ZONE_FEE, any_free_delivery=True) == Decimal("0.000")
    assert pricing.delivery_fee(ZONE_FEE, any_free_delivery=False) == ZONE_FEE


def test_line_total_is_unit_price_times_item_count() -> None:
    assert pricing.line_total(Line(Decimal("2.125"), 4)) == Decimal("8.500")
    assert pricing.line_total(Line(None, 4)) is None
