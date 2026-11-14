from decimal import Decimal
from typing import Self

from pydantic import BaseModel

from app.features.settings.models import Setting
from app.shared.governorates import DeliveryZone, Governorate
from app.shared.phone import to_international


class GovernorateDelivery(BaseModel):
    governorate: Governorate
    zone: DeliveryZone
    delivery_fee: Decimal

    @classmethod
    def from_settings(cls, governorate: Governorate, settings: Setting) -> Self:
        return cls(
            governorate=governorate,
            zone=governorate.zone,
            delivery_fee=settings.delivery_fee_for(governorate.zone),
        )


class PublicSettings(BaseModel):
    """What the storefront needs: delivery fees and contact links. No secrets."""

    zone_a_delivery_fee: Decimal
    zone_b_delivery_fee: Decimal
    governorates: list[GovernorateDelivery]
    """The 12 governorates in display order, each with its zone and current fee."""
    whatsapp_number: str
    """Local form, e.g. 0790087017."""
    whatsapp_international: str
    """For wa.me links, e.g. 962790087017."""
    instagram_url: str | None
    facebook_url: str | None

    @classmethod
    def from_settings(cls, settings: Setting) -> Self:
        return cls(
            zone_a_delivery_fee=settings.zone_a_delivery_fee,
            zone_b_delivery_fee=settings.zone_b_delivery_fee,
            governorates=[
                GovernorateDelivery.from_settings(governorate, settings)
                for governorate in Governorate
            ],
            whatsapp_number=settings.whatsapp_number,
            whatsapp_international=to_international(settings.whatsapp_number),
            instagram_url=settings.instagram_url,
            facebook_url=settings.facebook_url,
        )
