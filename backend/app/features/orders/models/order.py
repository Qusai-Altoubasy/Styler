from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Identity, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, SoftDeleteMixin, TimestampMixin, str_enum
from app.features.orders.enums import OrderStatus
from app.shared.governorates import Governorate
from app.shared.money import MONEY
from app.shared.phone import JORDAN_MOBILE_PATTERN

if TYPE_CHECKING:
    from app.features.orders.models.order_item import OrderItem

FIRST_ORDER_NUMBER = 1001


class Order(TimestampMixin, SoftDeleteMixin, Base):
    """A customer order. The order number shown everywhere is the `id` itself.

    `subtotal` sums the priced items only; quote items count once the manager prices
    them. `total` = `subtotal` + `delivery_fee`. Both are recalculated by the service
    whenever an item or a quote price changes.
    """

    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Identity(start=FIRST_ORDER_NUMBER), primary_key=True)
    customer_name: Mapped[str] = mapped_column(String(100))
    phone: Mapped[str] = mapped_column(String(10), index=True)
    governorate: Mapped[Governorate] = mapped_column(str_enum(Governorate, "governorate"))
    address: Mapped[str] = mapped_column(Text)
    delivery_fee: Mapped[Decimal] = mapped_column(MONEY)
    subtotal: Mapped[Decimal] = mapped_column(MONEY)
    total: Mapped[Decimal] = mapped_column(MONEY)
    internal_note: Mapped[str | None] = mapped_column(Text)
    """For the manager only. Never returned by the public API."""
    status: Mapped[OrderStatus | None] = mapped_column(str_enum(OrderStatus, "order_status"))

    items: Mapped[list[OrderItem]] = relationship(
        back_populates="order", order_by="OrderItem.id", lazy="raise"
    )

    __table_args__ = (
        CheckConstraint(f"phone ~ '{JORDAN_MOBILE_PATTERN}'", name="phone_format"),
        CheckConstraint("delivery_fee >= 0", name="delivery_fee_not_negative"),
        CheckConstraint("subtotal >= 0", name="subtotal_not_negative"),
        CheckConstraint("total >= 0", name="total_not_negative"),
        Index("ix_orders_created_at", "created_at"),
    )
