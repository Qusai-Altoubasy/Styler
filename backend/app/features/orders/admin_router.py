"""`/api/admin/orders`: the manager's order log. The mark and the note never reach the
customer, and nothing here sends a message."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.features.auth.dependencies import require_admin
from app.features.orders import service
from app.features.orders.schemas import (
    OrderDetail,
    OrderFilters,
    OrderPage,
    OrderStats,
    OrderUpdate,
)
from app.shared.ids import PathId

router = APIRouter(prefix="/orders", tags=["orders"], dependencies=[Depends(require_admin)])

Session = Annotated[AsyncSession, Depends(get_session)]


@router.get("")
async def list_orders(session: Session, filters: Annotated[OrderFilters, Query()]) -> OrderPage:
    """Newest first, filtered by mark and searched by name, phone or order number."""
    return OrderPage.from_page(await service.list_orders(session, filters), filters)


# Declared before `/{order_id}`, so "stats" is never read as an id.
@router.get("/stats")
async def get_stats(session: Session) -> OrderStats:
    return OrderStats.from_stats(await service.order_stats(session))


@router.get("/{order_id}")
async def get_order(session: Session, order_id: PathId) -> OrderDetail:
    return OrderDetail.from_order(await service.get_order(session, order_id))


@router.patch("/{order_id}")
async def update_order(session: Session, order_id: PathId, data: OrderUpdate) -> OrderDetail:
    """Set or clear the mark and the note, and price quote items (totals follow)."""
    return OrderDetail.from_order(await service.update_order(session, order_id, data))


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_order(session: Session, order_id: PathId) -> None:
    await service.delete_order(session, order_id)
