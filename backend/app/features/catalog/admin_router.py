"""`/api/admin/categories` and `/api/admin/products`: the manager's catalog."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.features.auth.dependencies import require_admin
from app.features.catalog import admin_service as service
from app.features.catalog.admin_schemas import (
    AdminCategoryOut,
    AdminProductFilters,
    AdminProductOut,
    AdminProductPage,
    CategoryCreate,
    CategoryUpdate,
    ProductCreate,
    ProductUpdate,
)
from app.shared.ids import PathId

router = APIRouter(tags=["catalog"], dependencies=[Depends(require_admin)])

Session = Annotated[AsyncSession, Depends(get_session)]


@router.get("/categories")
async def list_categories(session: Session) -> list[AdminCategoryOut]:
    """Every category, also those without products, in display order."""
    summaries = await service.list_categories(session)
    return [AdminCategoryOut.from_summary(summary) for summary in summaries]


@router.post("/categories", status_code=status.HTTP_201_CREATED)
async def create_category(session: Session, data: CategoryCreate) -> AdminCategoryOut:
    return AdminCategoryOut.from_summary(await service.create_category(session, data))


@router.patch("/categories/{category_id}")
async def update_category(
    session: Session, category_id: PathId, data: CategoryUpdate
) -> AdminCategoryOut:
    return AdminCategoryOut.from_summary(await service.update_category(session, category_id, data))


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(session: Session, category_id: PathId) -> None:
    """409 `category_has_products` while any product (hidden ones too) is in it."""
    await service.delete_category(session, category_id)


@router.get("/products")
async def list_products(
    session: Session, filters: Annotated[AdminProductFilters, Query()]
) -> AdminProductPage:
    """One page of products, hidden ones included, newest first, with tiers and colors."""
    return AdminProductPage.from_page(await service.list_products(session, filters), filters)


@router.post("/products", status_code=status.HTTP_201_CREATED)
async def create_product(session: Session, data: ProductCreate) -> AdminProductOut:
    return AdminProductOut.from_product(await service.create_product(session, data))


@router.get("/products/{product_id}")
async def get_product(session: Session, product_id: PathId) -> AdminProductOut:
    """One product for the edit form, hidden ones included. 404 `product_not_found`."""
    return AdminProductOut.from_product(await service.get_product(session, product_id))


@router.patch("/products/{product_id}")
async def update_product(
    session: Session, product_id: PathId, data: ProductUpdate
) -> AdminProductOut:
    """Changes only the fields sent; `is_visible` hides or shows the product."""
    return AdminProductOut.from_product(await service.update_product(session, product_id, data))


@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(session: Session, product_id: PathId) -> None:
    await service.delete_product(session, product_id)
