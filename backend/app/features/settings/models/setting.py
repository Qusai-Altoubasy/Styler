from decimal import Decimal

from sqlalchemy import CheckConstraint, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, SoftDeleteMixin, TimestampMixin
from app.shared.governorates import DeliveryZone
from app.shared.money import MONEY
from app.shared.phone import JORDAN_MOBILE_PATTERN

SETTINGS_ROW_ID = 1


class Setting(TimestampMixin, SoftDeleteMixin, Base):
    """The store settings: exactly one row (id = 1), seeded by migration 0009."""

    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=False, server_default=text(str(SETTINGS_ROW_ID))
    )
    """Always 1: inserting without an id creates the one row, a second insert fails."""
    zone_a_delivery_fee: Mapped[Decimal] = mapped_column(MONEY)
    zone_b_delivery_fee: Mapped[Decimal] = mapped_column(MONEY)
    whatsapp_number: Mapped[str] = mapped_column(String(10))
    instagram_url: Mapped[str | None] = mapped_column(String(500))
    facebook_url: Mapped[str | None] = mapped_column(String(500))
    admin_password_hash: Mapped[str | None] = mapped_column(String(255))
    """argon2 hash, set with cli/set_password.py. Never returned by any endpoint."""

    __table_args__ = (
        CheckConstraint(f"id = {SETTINGS_ROW_ID}", name="single_row"),
        CheckConstraint("zone_a_delivery_fee >= 0", name="zone_a_delivery_fee_not_negative"),
        CheckConstraint("zone_b_delivery_fee >= 0", name="zone_b_delivery_fee_not_negative"),
        CheckConstraint(f"whatsapp_number ~ '{JORDAN_MOBILE_PATTERN}'", name="whatsapp_format"),
    )

    def delivery_fee_for(self, zone: DeliveryZone) -> Decimal:
        match zone:
            case DeliveryZone.A:
                return self.zone_a_delivery_fee
            case DeliveryZone.B:
                return self.zone_b_delivery_fee
