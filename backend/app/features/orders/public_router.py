from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.features.orders import service
from app.features.orders.schemas import OrderConfirmation, OrderCreate

router = APIRouter(tags=["orders"])


@router.post("/orders", status_code=status.HTTP_201_CREATED)
async def create_order(
    session: Annotated[AsyncSession, Depends(get_session)], data: OrderCreate
) -> OrderConfirmation:
    """Save the order; the storefront then opens WhatsApp with the returned details."""
    return OrderConfirmation.model_validate(await service.create_order(session, data))
