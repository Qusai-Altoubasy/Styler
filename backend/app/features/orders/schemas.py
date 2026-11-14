"""What the order endpoints accept and return.

The browser sends only what the customer chose (product, tier, color, count). Every
price, the delivery fee and the totals are computed on the server.
"""

from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StringConstraints,
    computed_field,
)

from app.features.orders import pricing
from app.shared.governorates import Governorate
from app.shared.ids import DbId
from app.shared.phone import JORDAN_MOBILE_PATTERN, normalize_phone
from app.shared.pricing_mode import PricingMode
from app.shared.text import NoControlCharacters

MAX_ITEMS_PER_ORDER = 50
MAX_ITEM_COUNT = 10_000
"""No real maximum for the customer; this only keeps totals inside the MONEY column."""
MAX_APPROX_QUANTITY = 10_000_000


def _normalize_phone(value: object) -> object:
    """Accept the number as typed on a phone keyboard: Arabic digits, spaces, dashes."""
    return normalize_phone(value) if isinstance(value, str) else value


JordanMobile = Annotated[
    str,
    BeforeValidator(_normalize_phone),
    StringConstraints(pattern=JORDAN_MOBILE_PATTERN),
]
CustomerName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
    NoControlCharacters,
]
Address = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=500),
    NoControlCharacters,
]


class OrderItemIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_id: DbId
    tier_id: DbId | None = None
    """Required for `fixed` products: the chosen row of the quantity table."""
    approx_quantity: Annotated[int, Field(ge=1, le=MAX_APPROX_QUANTITY)] | None = None
    """Optional for `quote` products; not allowed for `fixed` ones."""
    color_id: DbId | None = None
    """Required when the product is available in colors, not allowed otherwise."""
    item_count: Annotated[int, Field(ge=1, le=MAX_ITEM_COUNT)] = 1


class OrderCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    customer_name: CustomerName
    phone: JordanMobile
    governorate: Governorate
    address: Address
    items: Annotated[list[OrderItemIn], Field(min_length=1, max_length=MAX_ITEMS_PER_ORDER)]


class OrderItemOut(BaseModel):
    """A frozen copy of the product as it was ordered. Built from an `OrderItem`."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int | None
    product_name_ar: str
    product_name_en: str
    pricing_mode: PricingMode
    quantity: int | None
    tier_note_ar: str | None
    tier_note_en: str | None
    color_name_ar: str | None
    color_name_en: str | None
    color_hex: str | None
    item_count: int
    unit_price: Decimal | None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def line_total(self) -> Decimal | None:
        """`unit_price * item_count`; null while a quote item is not priced."""
        return pricing.line_total(self)


class OrderConfirmation(BaseModel):
    """Returned to the customer: everything the WhatsApp message and the
    "We got your order" page need. No internal note and no mark. Built from an `Order`."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    """The order number, shown as a plain number."""
    created_at: datetime
    customer_name: str
    phone: str
    governorate: Governorate
    address: str
    items: list[OrderItemOut]
    delivery_fee: Decimal
    subtotal: Decimal
    total: Decimal

    @computed_field  # type: ignore[prop-decorator]
    @property
    def awaiting_quote(self) -> bool:
        """True when some items wait for a price: the total covers the priced ones only."""
        return pricing.awaiting_quote(self.items)
