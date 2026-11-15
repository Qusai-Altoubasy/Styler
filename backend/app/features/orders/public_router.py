from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.client_ip import ClientKey
from app.core.db import get_session
from app.core.rate_limit import RateLimiter
from app.features.orders import service
from app.features.orders.schemas import OrderConfirmation, OrderCreate

router = APIRouter(tags=["orders"])

order_attempts = RateLimiter(limit=10, window=timedelta(minutes=3))
"""Per IP. Generous: mobile carriers put many customers behind one IP (CGNAT)."""


@router.post("/orders", status_code=status.HTTP_201_CREATED)
async def create_order(
    session: Annotated[AsyncSession, Depends(get_session)], client: ClientKey, data: OrderCreate
) -> OrderConfirmation:
    """Save the order; the storefront then opens WhatsApp with the returned details."""
    order_attempts.acquire(client)
    return OrderConfirmation.model_validate(await service.create_order(session, data))
