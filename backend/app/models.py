"""Imports every model, so `Base.metadata` knows every table (used by Alembic)."""

from app.core.db import Base
from app.features.auth.models import AdminSession
from app.features.catalog.models import Category, Product, ProductColor, ProductPriceTier
from app.features.orders.models import Order, OrderItem
from app.features.settings.models import Setting

__all__ = [
    "AdminSession",
    "Base",
    "Category",
    "Order",
    "OrderItem",
    "Product",
    "ProductColor",
    "ProductPriceTier",
    "Setting",
]
