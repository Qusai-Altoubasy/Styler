"""What the catalog endpoints accept and return.

Money is a Decimal, sent in JSON as a string with 3 places ("7.000"). A product's
`price` is the lowest price in its quantity table; quote products have no price.
"""

from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING, Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.features.catalog.enums import BrandColor
from app.features.catalog.models import Product
from app.shared.ids import DbId
from app.shared.media import image_url
from app.shared.pricing_mode import PricingMode
from app.shared.text import NoControlCharacters

if TYPE_CHECKING:
    from app.features.catalog.service import CategorySummary, ProductSummary

SearchText = Annotated[
    str, StringConstraints(strip_whitespace=True, max_length=100), NoControlCharacters
]


class ProductSort(StrEnum):
    DEFAULT = "default"  # newest first
    PRICE_ASC = "price_asc"  # quote products last
    PRICE_DESC = "price_desc"  # quote products last
    NAME = "name"  # in the language given by `lang`


class Language(StrEnum):
    AR = "ar"
    EN = "en"


class ProductFilters(BaseModel):
    """Query parameters of `GET /api/products`. Every filter is optional."""

    category_id: DbId | None = None
    q: SearchText | None = None
    """Search in the Arabic and English names."""
    min_price: Annotated[Decimal, Field(ge=0, max_digits=10, decimal_places=3)] | None = None
    max_price: Annotated[Decimal, Field(ge=0, max_digits=10, decimal_places=3)] | None = None
    """Setting either price bound hides quote products, which have no price."""
    pricing_mode: PricingMode | None = None
    free_delivery: bool | None = None
    """`true` keeps only free-delivery products; `false` or absent applies no filter."""
    sort: ProductSort = ProductSort.DEFAULT
    lang: Language = Language.AR
    """Only used by `sort=name`."""


class CategoryCard(BaseModel):
    id: int
    name_ar: str
    name_en: str
    color: BrandColor
    image_url: str | None
    product_count: int
    """Visible products only."""
    min_price: Decimal | None
    """The lowest price among its visible products; null if all are quote products."""

    @classmethod
    def from_summary(cls, summary: CategorySummary) -> Self:
        category = summary.category
        return cls(
            id=category.id,
            name_ar=category.name_ar,
            name_en=category.name_en,
            color=category.color,
            image_url=image_url(category.image_key),
            product_count=summary.product_count,
            min_price=summary.min_price,
        )


class CategoryRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name_ar: str
    name_en: str


class ProductCard(BaseModel):
    id: int
    category_id: int
    name_ar: str
    name_en: str
    image_url: str | None
    pricing_mode: PricingMode
    free_delivery: bool
    price: Decimal | None
    """The lowest tier price ("from 7 JOD"); null for quote products."""
    has_colors: bool

    @classmethod
    def from_summary(cls, summary: ProductSummary) -> Self:
        product = summary.product
        return cls(
            id=product.id,
            category_id=product.category_id,
            name_ar=product.name_ar,
            name_en=product.name_en,
            image_url=image_url(product.image_key),
            pricing_mode=product.pricing_mode,
            free_delivery=product.free_delivery,
            price=summary.price,
            has_colors=summary.has_colors,
        )


class PriceTierOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    quantity: int
    price: Decimal
    note_ar: str | None
    note_en: str | None


class ColorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name_ar: str
    name_en: str
    hex: str


class ProductDetail(BaseModel):
    id: int
    category: CategoryRef
    name_ar: str
    name_en: str
    description_ar: str
    description_en: str
    image_url: str | None
    pricing_mode: PricingMode
    free_delivery: bool
    price: Decimal | None
    price_tiers: list[PriceTierOut]
    """Empty for quote products."""
    colors: list[ColorOut]
    """Empty when the product is not available in colors."""

    @classmethod
    def from_product(cls, product: Product) -> Self:
        """Needs the category, tiers and colors loaded."""
        return cls(
            id=product.id,
            category=CategoryRef.model_validate(product.category),
            name_ar=product.name_ar,
            name_en=product.name_en,
            description_ar=product.description_ar,
            description_en=product.description_en,
            image_url=image_url(product.image_key),
            pricing_mode=product.pricing_mode,
            free_delivery=product.free_delivery,
            price=product.lowest_price(),
            price_tiers=[PriceTierOut.model_validate(tier) for tier in product.offered_tiers()],
            colors=[ColorOut.model_validate(color) for color in product.colors],
        )
