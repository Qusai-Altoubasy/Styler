from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Identity, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, SoftDeleteMixin, TimestampMixin, str_enum
from app.shared.money import MONEY
from app.shared.pricing_mode import PricingMode

if TYPE_CHECKING:
    from app.features.orders.models.order import Order


class OrderItem(TimestampMixin, SoftDeleteMixin, Base):
    """One line of an order: a frozen copy of the product as it was when ordered.

    Editing, hiding or deleting the product later never changes this row.
    `product_id` is kept only as a reference and may point at a deleted product.

    - `fixed`: `quantity`, `tier_note_*` and `unit_price` come from the chosen tier.
    - `quote`: `quantity` is the customer's optional approximate quantity, and
      `unit_price` stays NULL until the manager sets the price.

    The line total is `unit_price * item_count`, or nothing while unpriced.
    """

    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Identity(), primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL"), index=True
    )
    product_name_ar: Mapped[str] = mapped_column(String(200))
    product_name_en: Mapped[str] = mapped_column(String(200))
    pricing_mode: Mapped[PricingMode] = mapped_column(str_enum(PricingMode, "pricing_mode"))
    quantity: Mapped[int | None]
    tier_note_ar: Mapped[str | None] = mapped_column(String(200))
    tier_note_en: Mapped[str | None] = mapped_column(String(200))
    color_name_ar: Mapped[str | None] = mapped_column(String(50))
    color_name_en: Mapped[str | None] = mapped_column(String(50))
    color_hex: Mapped[str | None] = mapped_column(String(7))
    item_count: Mapped[int]
    """How many of this line the customer wants: 1 or more, no maximum."""
    unit_price: Mapped[Decimal | None] = mapped_column(MONEY)

    order: Mapped[Order] = relationship(back_populates="items", lazy="raise")

    __table_args__ = (
        CheckConstraint("item_count >= 1", name="item_count_positive"),
        CheckConstraint("quantity IS NULL OR quantity > 0", name="quantity_positive"),
        CheckConstraint("unit_price IS NULL OR unit_price >= 0", name="unit_price_not_negative"),
        CheckConstraint(
            "pricing_mode = 'quote' OR (quantity IS NOT NULL AND unit_price IS NOT NULL)",
            name="fixed_item_is_priced",
        ),
    )
