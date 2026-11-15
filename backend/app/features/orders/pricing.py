"""Order totals and delivery: pure functions, no database.

Used when the customer places an order and again whenever the manager prices a
quote item, so both paths always compute the same numbers.

- A line's total is `unit_price * item_count`; a quote line has none until priced.
- `subtotal` sums the priced lines only; `total` = `subtotal` + delivery.
- Delivery is the zone fee, or free for the whole order when any product in it
  has free delivery.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

ZERO = Decimal("0.000")


class PricedLine(Protocol):
    """Anything with a unit price and a count: an `OrderItem`, or a `Line` in tests."""

    @property
    def unit_price(self) -> Decimal | None: ...

    @property
    def item_count(self) -> int: ...


@dataclass(frozen=True, slots=True)
class Line:
    unit_price: Decimal | None
    """None for a quote item the manager has not priced yet."""
    item_count: int


@dataclass(frozen=True, slots=True)
class Totals:
    subtotal: Decimal
    total: Decimal


def line_total(line: PricedLine) -> Decimal | None:
    return None if line.unit_price is None else line.unit_price * line.item_count


def awaiting_quote(lines: Iterable[PricedLine]) -> bool:
    """True while any line has no price: the total does not include it yet."""
    return any(line.unit_price is None for line in lines)


def delivery_fee(zone_fee: Decimal, *, any_free_delivery: bool) -> Decimal:
    return ZERO if any_free_delivery else zone_fee


def order_totals(lines: Sequence[PricedLine], delivery: Decimal) -> Totals:
    subtotal = sum((total for line in lines if (total := line_total(line)) is not None), ZERO)
    return Totals(subtotal=subtotal, total=subtotal + delivery)
