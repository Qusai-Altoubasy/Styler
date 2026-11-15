from decimal import Decimal
from typing import Annotated, Self
from urllib.parse import urlsplit

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    StringConstraints,
)

from app.features.settings.models import Setting
from app.shared.governorates import DeliveryZone, Governorate
from app.shared.money import MoneyIn
from app.shared.patch import PatchModel
from app.shared.phone import JORDAN_MOBILE_PATTERN, normalize_phone, to_international
from app.shared.text import NoControlCharacters


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


WhatsAppNumber = Annotated[
    str,
    BeforeValidator(lambda v: normalize_phone(v) if isinstance(v, str) else v),
    StringConstraints(pattern=JORDAN_MOBILE_PATTERN),
]
"""Typed like a customer phone (spaces, dashes, Arabic-Indic digits), stored as 10 digits."""


def _social_link(domain: str) -> AfterValidator:
    def check(value: str) -> str:
        parts = urlsplit(value)
        host = parts.hostname or ""
        if parts.scheme != "https" or parts.username or parts.password:
            raise ValueError("must be an https:// link")
        if host != domain and not host.endswith("." + domain):
            raise ValueError(f"must be a {domain} link")
        return value

    return AfterValidator(check)


def _empty_clears(value: object) -> object:
    """An empty box clears the link."""
    return None if isinstance(value, str) and not value.strip() else value


_LINK = StringConstraints(strip_whitespace=True, max_length=500, pattern=r"^\S+$")
InstagramLink = Annotated[
    Annotated[str, _LINK, NoControlCharacters, _social_link("instagram.com")] | None,
    BeforeValidator(_empty_clears),
]
FacebookLink = Annotated[
    Annotated[str, _LINK, NoControlCharacters, _social_link("facebook.com")] | None,
    BeforeValidator(_empty_clears),
]


class AdminSettings(BaseModel):
    """The settings the manager can edit. Built field by field: the password hash is
    never part of it."""

    zone_a_delivery_fee: Decimal
    zone_b_delivery_fee: Decimal
    whatsapp_number: str
    """Local form, e.g. 0790087017."""
    instagram_url: str | None
    facebook_url: str | None

    @classmethod
    def from_settings(cls, settings: Setting) -> Self:
        return cls(
            zone_a_delivery_fee=settings.zone_a_delivery_fee,
            zone_b_delivery_fee=settings.zone_b_delivery_fee,
            whatsapp_number=settings.whatsapp_number,
            instagram_url=settings.instagram_url,
            facebook_url=settings.facebook_url,
        )


class SettingsUpdate(PatchModel):
    """A partial update: only the fields sent change. A link may be null (or empty) to
    remove it; the fees and the WhatsApp number cannot be null."""

    NULLABLE = frozenset({"instagram_url", "facebook_url"})

    zone_a_delivery_fee: MoneyIn | None = None
    zone_b_delivery_fee: MoneyIn | None = None
    whatsapp_number: WhatsAppNumber | None = None
    instagram_url: InstagramLink = None
    facebook_url: FacebookLink = None
