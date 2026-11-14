from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.features.catalog import service
from app.features.catalog.schemas import CategoryCard, ProductCard, ProductDetail, ProductFilters
from app.shared.ids import PathId

router = APIRouter(tags=["catalog"])

Session = Annotated[AsyncSession, Depends(get_session)]


@router.get("/categories")
async def list_categories(session: Session) -> list[CategoryCard]:
    """Categories shown on the home page: only those with a visible product."""
    summaries = await service.list_visible_categories(session)
    return [CategoryCard.from_summary(summary) for summary in summaries]


@router.get("/products")
async def list_products(
    session: Session, filters: Annotated[ProductFilters, Query()]
) -> list[ProductCard]:
    summaries = await service.list_visible_products(session, filters)
    return [ProductCard.from_summary(summary) for summary in summaries]


@router.get("/products/{product_id}")
async def get_product(session: Session, product_id: PathId) -> ProductDetail:
    return ProductDetail.from_product(await service.get_visible_product(session, product_id))
