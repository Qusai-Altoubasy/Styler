"""The manager's catalog: categories and products, hidden ones included.

Every writing function commits its own work. Rows are removed with `soft_delete()`;
order items keep a frozen copy of the product, so editing or deleting a product never
changes an old order.

Images: the dashboard sends a `tmp/` key from the upload link (a new image), the row's
current `media/` key (keep it), or null (remove it). The upload is moved to `media/`
after every check passed and just before the commit; the image it replaces is deleted
after the commit. If the save fails after the move, the moved image is deleted again.
One image object belongs to one row only. Images of deleted rows are kept.
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import NamedTuple

from botocore.exceptions import BotoCoreError, ClientError
from sqlalchemy import ColumnElement, Select, exists, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.db import soft_delete
from app.core.errors import AppError, ConflictError, InvalidRequestError, NotFoundError
from app.features.catalog.admin_schemas import (
    AdminProductFilters,
    CategoryCreate,
    CategoryUpdate,
    ColorIn,
    PriceTierIn,
    ProductCreate,
    ProductUpdate,
)
from app.features.catalog.models import Category, Product, ProductColor, ProductPriceTier
from app.features.catalog.row_replacement import (
    avoid_unique_collisions,
    find_duplicate,
    plan_replacement,
)
from app.features.media import service as media_service
from app.features.media.keys import parse_image_key
from app.shared.text_search import LIKE_ESCAPE, contains_pattern

logger = logging.getLogger(__name__)

_CATEGORY_NAME_INDEXES = {
    "uq_categories_name_ar": "name_ar",
    "uq_categories_name_en": "name_en",
}
_TIER_INDEX = "uq_product_price_tiers_tier"

_PRODUCT_FIELDS = (
    "category_id",
    "name_ar",
    "name_en",
    "description_ar",
    "description_en",
    "pricing_mode",
    "free_delivery",
    "is_visible",
)
"""Product columns a create or a PATCH copies as they are."""

type TierKey = tuple[int, str | None, str | None]
"""What makes a tier unique within its product: quantity and the two notes."""


class AdminCategory(NamedTuple):
    category: Category
    product_count: int
    """Live products, hidden ones included."""


class CategoryNameTakenError(ConflictError):
    def __init__(self, field: str) -> None:
        super().__init__("category_name_taken", "A category with this name exists", field=field)


class DuplicateTierConflictError(ConflictError):
    """Another save added the same tier at the same moment (the unique index caught it).
    Within one request a duplicate is a 422 with the same code, found before saving."""

    def __init__(self) -> None:
        super().__init__("duplicate_price_tier", "This quantity and note already exist")


class ImageInUseError(InvalidRequestError):
    """The image already belongs to another row (a double-submitted save, or a key built
    from another row's image): sharing it would lose it when either row replaced it."""

    def __init__(self) -> None:
        super().__init__("image_in_use", "This image belongs to another item, upload it again")


class ProductsPage(NamedTuple):
    products: list[Product]
    """With their tiers and colors loaded."""
    total: int
    """Matching products across every page."""


class CategoryHasProductsError(ConflictError):
    def __init__(self, product_count: int) -> None:
        super().__init__(
            "category_has_products",
            "Move or delete the category's products first",
            product_count=product_count,
        )


# Categories


async def list_categories(session: AsyncSession) -> list[AdminCategory]:
    """Every live category, also those without products, in display order."""
    stmt = (
        select(Category, func.count(Product.id))
        .outerjoin(Product, Product.category_id == Category.id)
        .group_by(Category.id)
        .order_by(Category.sort_order, Category.id)
    )
    return [AdminCategory(*row) for row in await session.execute(stmt)]


async def create_category(session: AsyncSession, data: CategoryCreate) -> AdminCategory:
    category = Category(**data.model_dump(exclude={"image_key"}))
    async with _saving(session) as moved:
        session.add(category)
        await session.flush()
        category.image_key = await _store_image(session, data.image_key, None, moved)
        await session.commit()
    return await _category_summary(session, category.id)


async def update_category(
    session: AsyncSession, category_id: int, data: CategoryUpdate
) -> AdminCategory:
    category = await _get_category(session, category_id)
    old_image = category.image_key
    async with _saving(session) as moved:
        for field, value in data.model_dump(exclude_unset=True, exclude={"image_key"}).items():
            setattr(category, field, value)
        await session.flush()
        if "image_key" in data.model_fields_set:
            category.image_key = await _store_image(session, data.image_key, old_image, moved)
        await session.commit()
    await _delete_replaced_image(old_image, category.image_key)
    return await _category_summary(session, category_id)


async def delete_category(session: AsyncSession, category_id: int) -> None:
    """Refused while the category has a live product, even a hidden one."""
    category = await _get_category(session, category_id)
    product_count = await _count_products(session, category_id)
    if product_count:
        raise CategoryHasProductsError(product_count)
    await soft_delete(session, category)
    await session.commit()


async def _get_category(session: AsyncSession, category_id: int) -> Category:
    category = await session.get(Category, category_id)
    if category is None:
        raise NotFoundError("category_not_found", "Category not found", category_id=category_id)
    return category


async def _category_summary(session: AsyncSession, category_id: int) -> AdminCategory:
    category = await _get_category(session, category_id)
    return AdminCategory(category, await _count_products(session, category_id))


async def _count_products(session: AsyncSession, category_id: int) -> int:
    stmt = select(func.count(Product.id)).where(Product.category_id == category_id)
    return await session.scalar(stmt) or 0


def _violated_constraint(error: IntegrityError) -> str | None:
    driver_error = getattr(error.orig, "orig", None)
    return getattr(driver_error, "constraint_name", None)


# Products


async def list_products(session: AsyncSession, filters: AdminProductFilters) -> ProductsPage:
    """One page of live products, hidden ones included, newest first, with the count."""
    conditions = _product_conditions(filters)
    total = await session.scalar(select(func.count(Product.id)).where(*conditions)) or 0
    stmt = (
        _products_with_rows()
        .where(*conditions)
        .order_by(Product.id.desc())
        .limit(filters.limit)
        .offset(filters.offset)
    )
    return ProductsPage(products=list(await session.scalars(stmt)), total=total)


async def create_product(session: AsyncSession, data: ProductCreate) -> Product:
    await _check_category(session, data.category_id)
    product = Product(**data.model_dump(include=set(_PRODUCT_FIELDS)))
    async with _saving(session) as moved:
        session.add(product)
        await session.flush()
        await _replace_tiers(session, product.id, [], data.price_tiers)
        await _replace_colors(session, product.id, [], data.colors)
        product.image_key = await _store_image(session, data.image_key, None, moved)
        await session.commit()
    return await _get_product(session, product.id)


async def update_product(session: AsyncSession, product_id: int, data: ProductUpdate) -> Product:
    """Changes only the fields sent. A sent tier or color list replaces the current one."""
    product = await _get_product(session, product_id)
    old_image = product.image_key
    sent = data.model_fields_set
    if data.category_id is not None:
        await _check_category(session, data.category_id)
    async with _saving(session) as moved:
        for field, value in data.model_dump(include=set(_PRODUCT_FIELDS) & sent).items():
            setattr(product, field, value)
        if data.price_tiers is not None:
            await _replace_tiers(session, product_id, product.price_tiers, data.price_tiers)
        if data.colors is not None:
            await _replace_colors(session, product_id, product.colors, data.colors)
        if "image_key" in sent:
            product.image_key = await _store_image(session, data.image_key, old_image, moved)
        await session.commit()
    await _delete_replaced_image(old_image, product.image_key)
    return await _get_product(session, product_id)


async def delete_product(session: AsyncSession, product_id: int) -> None:
    """Gone from the store and the dashboard; old orders keep their frozen copy."""
    product = await _get_product(session, product_id)
    await soft_delete(session, product)
    await session.commit()


def _products_with_rows() -> Select[Product]:
    return select(Product).options(selectinload(Product.price_tiers), selectinload(Product.colors))


def _product_conditions(filters: AdminProductFilters) -> list[ColumnElement[bool]]:
    conditions: list[ColumnElement[bool]] = []
    if filters.category_id is not None:
        conditions.append(Product.category_id == filters.category_id)
    if filters.q:
        pattern = contains_pattern(filters.q)
        conditions.append(
            or_(
                Product.name_ar.ilike(pattern, escape=LIKE_ESCAPE),
                Product.name_en.ilike(pattern, escape=LIKE_ESCAPE),
            )
        )
    if filters.is_visible is not None:
        conditions.append(Product.is_visible.is_(filters.is_visible))
    return conditions


async def _get_product(session: AsyncSession, product_id: int) -> Product:
    """A live product with its live tiers and colors, freshly loaded."""
    stmt = (
        _products_with_rows()
        .where(Product.id == product_id)
        .execution_options(populate_existing=True)
    )
    product = await session.scalar(stmt)
    if product is None:
        raise NotFoundError("product_not_found", "Product not found", product_id=product_id)
    return product


async def _check_category(session: AsyncSession, category_id: int) -> None:
    if await session.get(Category, category_id) is None:
        raise InvalidRequestError(
            "category_not_found", "Choose an existing category", category_id=category_id
        )


async def _replace_tiers(
    session: AsyncSession,
    product_id: int,
    live: list[ProductPriceTier],
    sent: list[PriceTierIn],
) -> None:
    """Make the product's live tiers exactly `sent`, keeping the ids of matched rows.

    Removals are flushed before updates, and updates before inserts, so a tier removed
    and added again in the same save never clashes with the unique index.
    """
    sent_keys = [_tier_key(tier) for tier in sent]
    duplicate = find_duplicate(sent_keys)
    if duplicate is not None:
        raise InvalidRequestError(
            "duplicate_price_tier", "The same quantity and note appear twice", index=duplicate
        )
    by_id = {tier.id: tier for tier in live}
    plan = plan_replacement(by_id.keys(), [tier.id for tier in sent], row_name="price_tier")
    live_keys = {tier.id: _tier_key(tier) for tier in live}
    plan = avoid_unique_collisions(plan, live_keys, sent_keys)
    for tier_id in plan.removed:
        await soft_delete(session, by_id[tier_id])
    for tier_id, index in plan.updated:
        _copy_tier(by_id[tier_id], sent[index])
    await session.flush()
    for index in plan.added:
        tier = ProductPriceTier(product_id=product_id)
        _copy_tier(tier, sent[index])
        session.add(tier)
    await session.flush()


def _tier_key(tier: PriceTierIn | ProductPriceTier) -> TierKey:
    return tier.quantity, tier.note_ar, tier.note_en


def _copy_tier(row: ProductPriceTier, tier: PriceTierIn) -> None:
    row.quantity = tier.quantity
    row.price = tier.price
    row.note_ar = tier.note_ar
    row.note_en = tier.note_en


async def _replace_colors(
    session: AsyncSession, product_id: int, live: list[ProductColor], sent: list[ColorIn]
) -> None:
    """Make the product's live colors exactly `sent`, in that order, keeping the ids of
    matched rows."""
    by_id = {color.id: color for color in live}
    plan = plan_replacement(by_id.keys(), [color.id for color in sent], row_name="color")
    for color_id in plan.removed:
        await soft_delete(session, by_id[color_id])
    for color_id, index in plan.updated:
        _copy_color(by_id[color_id], sent[index], index)
    for index in plan.added:
        color = ProductColor(product_id=product_id)
        _copy_color(color, sent[index], index)
        session.add(color)
    await session.flush()


def _copy_color(row: ProductColor, color: ColorIn, sort_order: int) -> None:
    row.name_ar = color.name_ar
    row.name_en = color.name_en
    row.hex = color.hex
    row.sort_order = sort_order


# Saving and images


class _MovedImage:
    """The image a save moved into `media/` in this request, if any."""

    def __init__(self) -> None:
        self.key: str | None = None


@asynccontextmanager
async def _saving(session: AsyncSession) -> AsyncIterator[_MovedImage]:
    """Wraps a save up to and including its commit.

    A clash on a unique index becomes a clean error. On any failure, an image this save
    moved to `media/` is deleted again, so nothing is left unreferenced; the row's
    previous image is never touched.
    """
    moved = _MovedImage()
    try:
        yield moved
    except IntegrityError as error:
        await session.rollback()
        await _discard_image(moved.key)
        clash = _unique_clash(error)
        if clash is None:
            raise
        raise clash from error
    except BaseException:
        await _discard_image(moved.key)
        raise


def _unique_clash(error: IntegrityError) -> AppError | None:
    constraint = _violated_constraint(error)
    if constraint in _CATEGORY_NAME_INDEXES:
        return CategoryNameTakenError(_CATEGORY_NAME_INDEXES[constraint])
    if constraint == _TIER_INDEX:
        return DuplicateTierConflictError()
    return None


async def _store_image(
    session: AsyncSession, image_key: str | None, current: str | None, moved: _MovedImage
) -> str | None:
    """The key to store for the image the dashboard sent; moves a new upload to `media/`.

    A `media/` key is accepted only when it is the row's current image, and a saved image
    must not belong to another row (live or deleted): two rows sharing one object would
    lose it when either replaced its image. A retried save still works: its own row
    holds the key, or nothing does when the first attempt never committed.

    Saves of the same image wait for each other (`_claim_image`), so of two requests
    sent at once (a double tap) the second sees the first one's row and is refused
    without touching the object.
    """
    if image_key is None:
        return None
    key = parse_image_key(image_key)
    if key is None:
        raise media_service.InvalidImageKeyError()
    if key.media_key == current:
        return current
    if key.is_saved:
        raise media_service.InvalidImageKeyError()
    await _claim_image(session, key.media_key)
    if await _image_in_use(session, key.media_key):
        raise ImageInUseError()
    stored = await media_service.save_image(image_key)
    # Sole claimant under the lock: if this save fails, no row owns the object.
    moved.key = stored
    return stored


async def _claim_image(session: AsyncSession, media_key: str) -> None:
    """Hold a lock on this image until the transaction ends (commit or rollback)."""
    await session.execute(select(func.pg_advisory_xact_lock(func.hashtextextended(media_key, 0))))


async def _image_in_use(session: AsyncSession, image_key: str) -> bool:
    stmt = select(
        or_(
            exists().where(Category.image_key == image_key),
            exists().where(Product.image_key == image_key),
        )
    ).execution_options(include_deleted=True)
    return bool(await session.scalar(stmt))


async def _delete_replaced_image(old_key: str | None, new_key: str | None) -> None:
    """Call after the commit that stopped using `old_key`."""
    if old_key != new_key:
        await _discard_image(old_key)


async def _discard_image(image_key: str | None) -> None:
    """Deletes an image no row uses any more, best effort.

    A storage failure only leaves an orphaned image (logged) and never fails the request.
    An `InvalidImageKeyError` is not caught: a key of the wrong shape here is a bug, and
    should be loud.
    """
    if image_key is None:
        return
    try:
        await media_service.delete_image(image_key)
    except ClientError, BotoCoreError:
        logger.warning("Could not delete the image %s", image_key, exc_info=True)
