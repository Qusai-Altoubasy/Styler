from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Identity, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import SOFT_DELETE_FILTER, Base, SoftDeleteMixin, TimestampMixin
from app.shared.money import MONEY

if TYPE_CHECKING:
    from app.features.catalog.models.product import Product


class ProductPriceTier(TimestampMixin, SoftDeleteMixin, Base):
    """One row of a `fixed` product's quantity table, e.g. 250 pcs · 4 cm = 7 JOD.

    The same quantity may appear more than once with a different note
    (250 pcs · 4 cm and 250 pcs · 6 cm); only an exact duplicate is refused.
    """

    __tablename__ = "product_price_tiers"

    id: Mapped[int] = mapped_column(Identity(), primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    quantity: Mapped[int]
    price: Mapped[Decimal] = mapped_column(MONEY)
    note_ar: Mapped[str | None] = mapped_column(String(200))
    note_en: Mapped[str | None] = mapped_column(String(200))

    product: Mapped[Product] = relationship(back_populates="price_tiers", lazy="raise")

    __table_args__ = (
        CheckConstraint("quantity > 0", name="quantity_positive"),
        CheckConstraint("price >= 0", name="price_not_negative"),
        Index(
            "uq_product_price_tiers_tier",
            "product_id",
            "quantity",
            "note_ar",
            "note_en",
            unique=True,
            postgresql_nulls_not_distinct=True,
            postgresql_where=text(SOFT_DELETE_FILTER),
        ),
    )
