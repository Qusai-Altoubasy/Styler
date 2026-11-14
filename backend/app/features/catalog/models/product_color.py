from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Identity, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, SoftDeleteMixin, TimestampMixin
from app.shared.hex_color import HEX_COLOR_PATTERN

if TYPE_CHECKING:
    from app.features.catalog.models.product import Product


class ProductColor(TimestampMixin, SoftDeleteMixin, Base):
    """A color the customer can pick. Appearance only: no price change, no stock."""

    __tablename__ = "product_colors"

    id: Mapped[int] = mapped_column(Identity(), primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    name_ar: Mapped[str] = mapped_column(String(50))
    name_en: Mapped[str] = mapped_column(String(50))
    hex: Mapped[str] = mapped_column(String(7))
    sort_order: Mapped[int] = mapped_column(server_default=text("0"))

    product: Mapped[Product] = relationship(back_populates="colors", lazy="raise")

    __table_args__ = (CheckConstraint(f"hex ~ '{HEX_COLOR_PATTERN}'", name="hex_format"),)
