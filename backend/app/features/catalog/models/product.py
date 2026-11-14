from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Identity, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, SoftDeleteMixin, TimestampMixin, str_enum
from app.shared.pricing_mode import PricingMode

if TYPE_CHECKING:
    from app.features.catalog.models.category import Category
    from app.features.catalog.models.product_color import ProductColor
    from app.features.catalog.models.product_price_tier import ProductPriceTier


class Product(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Identity(), primary_key=True)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"), index=True
    )
    name_ar: Mapped[str] = mapped_column(String(200))
    name_en: Mapped[str] = mapped_column(String(200))
    description_ar: Mapped[str] = mapped_column(Text, server_default=text("''"))
    description_en: Mapped[str] = mapped_column(Text, server_default=text("''"))
    image_key: Mapped[str | None] = mapped_column(String(255))
    """S3 key under media/, e.g. `media/<uuid>.webp`. The URL is built from settings."""
    pricing_mode: Mapped[PricingMode] = mapped_column(str_enum(PricingMode, "pricing_mode"))
    free_delivery: Mapped[bool] = mapped_column(server_default=text("false"))
    is_visible: Mapped[bool] = mapped_column(server_default=text("true"))

    category: Mapped[Category] = relationship(back_populates="products", lazy="raise")
    price_tiers: Mapped[list[ProductPriceTier]] = relationship(
        back_populates="product",
        order_by="ProductPriceTier.quantity, ProductPriceTier.id",
        lazy="raise",
    )
    colors: Mapped[list[ProductColor]] = relationship(
        back_populates="product",
        order_by="ProductColor.sort_order, ProductColor.id",
        lazy="raise",
    )
    """"Available in colors" is on when the product has at least one color."""

    def offered_tiers(self) -> list[ProductPriceTier]:
        """The quantity table the customer chooses from (tiers must be loaded).

        Only a `fixed` product offers tiers: a `quote` product that still has rows
        (switched from `fixed`) offers none, and has no price.
        """
        return self.price_tiers if self.pricing_mode == PricingMode.FIXED else []

    def lowest_price(self) -> Decimal | None:
        """The product's price: the lowest offered tier. The same rule as the SQL in
        `catalog.service._product_prices()`."""
        return min((tier.price for tier in self.offered_tiers()), default=None)
