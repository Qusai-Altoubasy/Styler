"""What the dashboard's catalog endpoints accept and return.

Inputs refuse unknown fields. A PATCH body changes only the fields it carries; `null` is
allowed only where the value is optional (the image, the tier notes).
"""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Annotated, Self

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StringConstraints,
)

from app.features.catalog.enums import BrandColor
from app.features.catalog.models import Product
from app.features.catalog.schemas import ColorOut, PriceTierOut
from app.shared.hex_color import HEX_COLOR_PATTERN
from app.shared.ids import MAX_DB_ID, DbId
from app.shared.media import image_url
from app.shared.money import MoneyIn
from app.shared.patch import PatchModel
from app.shared.pricing_mode import PricingMode
from app.shared.text import NoControlCharacters, SearchText

if TYPE_CHECKING:
    from app.features.catalog.admin_service import AdminCategory, ProductsPage

MAX_PRICE_TIERS = 50
MAX_COLORS = 30
MAX_DESCRIPTION_LENGTH = 5000
MAX_PAGE_SIZE = 100
MAX_OFFSET = 1_000_000
"""Paging limits, the same as the orders log."""


def _name(max_length: int) -> object:
    return StringConstraints(strip_whitespace=True, min_length=1, max_length=max_length)


def _empty_to_none(value: str | None) -> str | None:
    return value or None


def _lowercase(value: object) -> object:
    return value.lower() if isinstance(value, str) else value


CategoryName = Annotated[str, _name(100), NoControlCharacters]
ProductName = Annotated[str, _name(200), NoControlCharacters]
ColorName = Annotated[str, _name(50), NoControlCharacters]
Description = Annotated[
    str,
    StringConstraints(strip_whitespace=True, max_length=MAX_DESCRIPTION_LENGTH),
    NoControlCharacters,
]
TierNote = Annotated[
    str,
    StringConstraints(strip_whitespace=True, max_length=200),
    NoControlCharacters,
    AfterValidator(_empty_to_none),
]
"""Optional: an empty note is stored as null, so "" and null are the same tier."""
HexColor = Annotated[str, BeforeValidator(_lowercase), StringConstraints(pattern=HEX_COLOR_PATTERN)]
"""`#rrggbb`; upper case is accepted and stored in lower case."""
Quantity = Annotated[int, Field(ge=1, le=MAX_DB_ID)]
SortOrder = Annotated[int, Field(ge=0, le=MAX_DB_ID)]
ImageKeyIn = Annotated[str, StringConstraints(max_length=255)]
"""A `tmp/` key from the upload link, or the row's current `media/` key to keep it."""


class _Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


# Categories


class CategoryCreate(_Input):
    name_ar: CategoryName
    name_en: CategoryName
    color: BrandColor
    image_key: ImageKeyIn | None = None
    sort_order: SortOrder = 0


class CategoryUpdate(PatchModel):
    NULLABLE = frozenset({"image_key"})

    name_ar: CategoryName | None = None
    name_en: CategoryName | None = None
    color: BrandColor | None = None
    image_key: ImageKeyIn | None = None
    """`null` removes the image."""
    sort_order: SortOrder | None = None


class AdminCategoryOut(BaseModel):
    id: int
    name_ar: str
    name_en: str
    color: BrandColor
    image_key: str | None
    image_url: str | None
    sort_order: int
    product_count: int
    """Every live product, hidden ones included: a category with any cannot be deleted."""

    @classmethod
    def from_summary(cls, summary: AdminCategory) -> Self:
        category = summary.category
        return cls(
            id=category.id,
            name_ar=category.name_ar,
            name_en=category.name_en,
            color=category.color,
            image_key=category.image_key,
            image_url=image_url(category.image_key),
            sort_order=category.sort_order,
            product_count=summary.product_count,
        )


# Products


class PriceTierIn(_Input):
    id: DbId | None = None
    """An existing row to update in place (its id stays the same); absent for a new row."""
    quantity: Quantity
    price: MoneyIn
    note_ar: TierNote | None = None
    note_en: TierNote | None = None


class ColorIn(_Input):
    id: DbId | None = None
    """An existing color to update in place (its id stays the same); absent for a new one."""
    name_ar: ColorName
    name_en: ColorName
    hex: HexColor


PriceTiers = Annotated[list[PriceTierIn], Field(max_length=MAX_PRICE_TIERS)]
"""The whole quantity table: it replaces the current one."""
Colors = Annotated[list[ColorIn], Field(max_length=MAX_COLORS)]
"""Every color in display order: the list replaces the current one. Empty = no colors."""


class ProductCreate(_Input):
    category_id: DbId
    name_ar: ProductName
    name_en: ProductName
    description_ar: Description = ""
    description_en: Description = ""
    image_key: ImageKeyIn | None = None
    pricing_mode: PricingMode
    free_delivery: bool = False
    is_visible: bool = True
    price_tiers: PriceTiers = []
    """A `fixed` product without tiers is saved but not shown in the store."""
    colors: Colors = []


class ProductUpdate(PatchModel):
    NULLABLE = frozenset({"image_key"})

    category_id: DbId | None = None
    name_ar: ProductName | None = None
    name_en: ProductName | None = None
    description_ar: Description | None = None
    description_en: Description | None = None
    image_key: ImageKeyIn | None = None
    """`null` removes the image."""
    pricing_mode: PricingMode | None = None
    free_delivery: bool | None = None
    is_visible: bool | None = None
    """Hide or show the product in the store."""
    price_tiers: PriceTiers | None = None
    colors: Colors | None = None


class AdminProductFilters(BaseModel):
    """Query parameters of `GET /api/admin/products`. Every filter is optional."""

    model_config = ConfigDict(extra="forbid")

    category_id: DbId | None = None
    q: SearchText | None = None
    """Search in the Arabic and English names."""
    is_visible: bool | None = None
    limit: Annotated[int, Field(ge=1, le=MAX_PAGE_SIZE)] = 50
    offset: Annotated[int, Field(ge=0, le=MAX_OFFSET)] = 0


class AdminProductOut(BaseModel):
    """Everything the dashboard's list and edit form need, hidden products included."""

    id: int
    category_id: int
    name_ar: str
    name_en: str
    description_ar: str
    description_en: str
    image_key: str | None
    image_url: str | None
    pricing_mode: PricingMode
    free_delivery: bool
    is_visible: bool
    shown_in_store: bool
    """Visible and orderable: false for a hidden product, or a `fixed` one without tiers."""
    price: Decimal | None
    """The lowest tier price; null for quote products."""
    price_tiers: list[PriceTierOut]
    """Every live row, also the ones a `quote` product keeps from when it was `fixed`."""
    colors: list[ColorOut]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_product(cls, product: Product) -> Self:
        """Needs the tiers and colors loaded."""
        return cls(
            id=product.id,
            category_id=product.category_id,
            name_ar=product.name_ar,
            name_en=product.name_en,
            description_ar=product.description_ar,
            description_en=product.description_en,
            image_key=product.image_key,
            image_url=image_url(product.image_key),
            pricing_mode=product.pricing_mode,
            free_delivery=product.free_delivery,
            is_visible=product.is_visible,
            shown_in_store=product.is_shown_in_store(),
            price=product.lowest_price(),
            price_tiers=[PriceTierOut.model_validate(tier) for tier in product.price_tiers],
            colors=[ColorOut.model_validate(color) for color in product.colors],
            created_at=product.created_at,
            updated_at=product.updated_at,
        )


class AdminProductPage(BaseModel):
    items: list[AdminProductOut]
    total: int
    """How many products match the filters, across every page."""
    limit: int
    offset: int

    @classmethod
    def from_page(cls, page: ProductsPage, filters: AdminProductFilters) -> Self:
        return cls(
            items=[AdminProductOut.from_product(product) for product in page.products],
            total=page.total,
            limit=filters.limit,
            offset=filters.offset,
        )
