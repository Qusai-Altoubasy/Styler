"""What the order endpoints accept and return.

The browser sends only what the customer chose (product, tier, color, count). Every
price, the delivery fee and the totals are computed on the server.
"""

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING, Annotated, Self

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StringConstraints,
    computed_field,
    field_validator,
)

from app.features.orders import pricing
from app.features.orders.enums import OrderStatus
from app.features.orders.models import Order
from app.shared.governorates import Governorate
from app.shared.ids import DbId
from app.shared.money import MoneyIn
from app.shared.patch import PatchModel
from app.shared.phone import JORDAN_MOBILE_PATTERN, normalize_phone, to_international
from app.shared.pricing_mode import PricingMode
from app.shared.text import NoControlCharacters, SearchText

if TYPE_CHECKING:
    from app.features.orders.service import OrdersPage, OrderStatsResult

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


# --- The manager's order log (`/api/admin/orders`) ---------------------------------

MAX_PAGE_SIZE = 100
MAX_OFFSET = 1_000_000
"""Far beyond any real log; only keeps the OFFSET a sane number."""
MAX_NOTE_LENGTH = 2000


InternalNote = Annotated[
    str,
    StringConstraints(strip_whitespace=True, max_length=MAX_NOTE_LENGTH),
    NoControlCharacters,
]


class MarkFilter(StrEnum):
    ALL = "all"
    UNMARKED = "unmarked"
    DONE = "done"
    CANCELLED = "cancelled"


class OrderFilters(BaseModel):
    """Query parameters of `GET /api/admin/orders`. Newest first."""

    model_config = ConfigDict(extra="forbid")

    status: MarkFilter = MarkFilter.ALL
    q: SearchText | None = None
    """The customer's name, a phone number (whole or part, as typed), or an order number."""
    limit: Annotated[int, Field(ge=1, le=MAX_PAGE_SIZE)] = 50
    offset: Annotated[int, Field(ge=0, le=MAX_OFFSET)] = 0


class OrderedProduct(BaseModel):
    """One line of the products column: the frozen name and how many."""

    model_config = ConfigDict(from_attributes=True)

    product_name_ar: str
    product_name_en: str
    item_count: int


class OrderRow(BaseModel):
    """One row of the orders table. Built from an `Order` with its items loaded."""

    id: int
    """The order number."""
    created_at: datetime
    customer_name: str
    phone: str
    governorate: Governorate
    products: list[OrderedProduct]
    total: Decimal
    status: OrderStatus | None
    """The manager's mark: null (not marked), `done` or `cancelled`."""
    awaiting_quote: bool
    """Some quote item has no price yet: the total does not include it."""

    @classmethod
    def from_order(cls, order: Order) -> Self:
        return cls(
            id=order.id,
            created_at=order.created_at,
            customer_name=order.customer_name,
            phone=order.phone,
            governorate=order.governorate,
            products=[OrderedProduct.model_validate(item) for item in order.items],
            total=order.total,
            status=order.status,
            awaiting_quote=pricing.awaiting_quote(order.items),
        )


class OrderPage(BaseModel):
    items: list[OrderRow]
    total: int
    """How many orders match the filters, across every page."""
    limit: int
    offset: int

    @classmethod
    def from_page(cls, page: OrdersPage, filters: OrderFilters) -> Self:
        return cls(
            items=[OrderRow.from_order(order) for order in page.orders],
            total=page.total,
            limit=filters.limit,
            offset=filters.offset,
        )


class OrderStats(BaseModel):
    """The quick numbers above the orders table. Deleted orders count nowhere."""

    all_orders: int
    """Every order, cancelled ones included."""
    today_orders: int
    """Orders placed today in Jordan (Asia/Amman), cancelled ones included."""
    quote_orders: int
    """Orders containing any quote item, priced or not, cancelled ones included."""
    orders_value: Decimal
    """The sum of `total` over every order that is not cancelled."""

    @classmethod
    def from_stats(cls, stats: OrderStatsResult) -> Self:
        return cls(
            all_orders=stats.all_orders,
            today_orders=stats.today_orders,
            quote_orders=stats.quote_orders,
            orders_value=stats.orders_value.quantize(pricing.ZERO),
        )


class OrderDetail(BaseModel):
    """Everything the manager sees for one order. Built from an `Order` with its items."""

    id: int
    created_at: datetime
    customer_name: str
    phone: str
    whatsapp_number: str
    """International form (9627XXXXXXXX) for the link that opens the customer's chat."""
    governorate: Governorate
    address: str
    items: list[OrderItemOut]
    delivery_fee: Decimal
    subtotal: Decimal
    total: Decimal
    awaiting_quote: bool
    internal_note: str | None
    status: OrderStatus | None

    @classmethod
    def from_order(cls, order: Order) -> Self:
        return cls(
            id=order.id,
            created_at=order.created_at,
            customer_name=order.customer_name,
            phone=order.phone,
            whatsapp_number=to_international(order.phone),
            governorate=order.governorate,
            address=order.address,
            items=[OrderItemOut.model_validate(item) for item in order.items],
            delivery_fee=order.delivery_fee,
            subtotal=order.subtotal,
            total=order.total,
            awaiting_quote=pricing.awaiting_quote(order.items),
            internal_note=order.internal_note,
            status=order.status,
        )


class ItemPriceIn(BaseModel):
    """The price of one quote item, per piece. `null` clears it (awaiting a price again)."""

    model_config = ConfigDict(extra="forbid")

    item_id: DbId
    unit_price: MoneyIn | None


class OrderUpdate(PatchModel):
    """`PATCH /api/admin/orders/{id}`. Only the fields sent are changed.

    `status: null` clears the mark and `internal_note: null` (or "") clears the note;
    leaving a field out keeps it as it is. `item_prices` cannot be null.
    """

    NULLABLE = frozenset({"status", "internal_note"})

    status: OrderStatus | None = None
    internal_note: InternalNote | None = None
    item_prices: list[ItemPriceIn] = Field(default_factory=list, max_length=MAX_ITEMS_PER_ORDER)

    @field_validator("item_prices")
    @classmethod
    def _one_price_per_item(cls, prices: list[ItemPriceIn]) -> list[ItemPriceIn]:
        if len({price.item_id for price in prices}) != len(prices):
            raise ValueError("each item may appear only once")
        return prices

    @field_validator("internal_note")
    @classmethod
    def _empty_note_clears(cls, note: str | None) -> str | None:
        return note or None

    @property
    def sets_status(self) -> bool:
        return "status" in self.model_fields_set

    @property
    def sets_internal_note(self) -> bool:
        return "internal_note" in self.model_fields_set
