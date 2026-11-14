from typing import TYPE_CHECKING

from sqlalchemy import Identity, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import SOFT_DELETE_FILTER, Base, SoftDeleteMixin, TimestampMixin, str_enum
from app.features.catalog.enums import BrandColor

if TYPE_CHECKING:
    from app.features.catalog.models.product import Product


class Category(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Identity(), primary_key=True)
    name_ar: Mapped[str] = mapped_column(String(100))
    name_en: Mapped[str] = mapped_column(String(100))
    color: Mapped[BrandColor] = mapped_column(str_enum(BrandColor, "brand_color"))
    image_key: Mapped[str | None] = mapped_column(String(255))
    """S3 key under media/, e.g. `media/<uuid>.webp`. The URL is built from settings."""
    sort_order: Mapped[int] = mapped_column(server_default=text("0"))

    products: Mapped[list[Product]] = relationship(back_populates="category", lazy="raise")

    __table_args__ = (
        # Unique ignoring case and surrounding spaces: "Mugs" and " mugs " clash.
        Index(
            "uq_categories_name_ar",
            text("lower(btrim(name_ar))"),
            unique=True,
            postgresql_where=text(SOFT_DELETE_FILTER),
        ),
        Index(
            "uq_categories_name_en",
            text("lower(btrim(name_en))"),
            unique=True,
            postgresql_where=text(SOFT_DELETE_FILTER),
        ),
    )
