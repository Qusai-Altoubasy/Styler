from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ColumnElement, ForeignKey, Identity, String, Text, exists, text
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

    # "Shown in the store" means visible and orderable: a `quote` product always, a
    # `fixed` one only with at least one live tier. The two methods below are the same
    # rule, in Python and in SQL; change them together.

    def is_shown_in_store(self) -> bool:
        """Whether customers see the product (tiers must be loaded)."""
        return self.is_visible and (
            self.pricing_mode == PricingMode.QUOTE or bool(self.price_tiers)
        )

    @classmethod
    def shown_in_store(cls) -> ColumnElement[bool]:
        """`is_shown_in_store()` as a WHERE condition. Soft-deleted tiers are left out of
        the EXISTS by the global filter in `app.core.db`."""
        from app.features.catalog.models.product_price_tier import ProductPriceTier

        has_tier = exists().where(ProductPriceTier.product_id == cls.id)
        return cls.is_visible & ((cls.pricing_mode == PricingMode.QUOTE) | has_tier)

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
