"""Creates the FastAPI app and registers the routers."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, Response, status
from sqlalchemy import text

from app.core.db import engine
from app.core.errors import register_error_handlers
from app.features.auth.admin_router import open_router as auth_open_router
from app.features.auth.admin_router import router as auth_admin_router
from app.features.catalog.public_router import router as catalog_public_router
from app.features.orders.public_router import router as orders_public_router
from app.features.settings.public_router import router as settings_public_router


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    await engine.dispose()


app = FastAPI(title="Styler API", lifespan=lifespan)
register_error_handlers(app)

# The storefront's API: no login. Served on the main domain under /api/*.
public_api = APIRouter(prefix="/api")
public_api.include_router(catalog_public_router)
public_api.include_router(orders_public_router)
public_api.include_router(settings_public_router)
app.include_router(public_api)

# The dashboard's API: every router behind a manager session, except login and logout.
# Served on the admin domain only (Caddy refuses /api/admin/* elsewhere).
admin_api = APIRouter(prefix="/api/admin")
admin_api.include_router(auth_open_router)
admin_api.include_router(auth_admin_router)
app.include_router(admin_api)


@app.get("/health", tags=["health"])
async def health(response: Response) -> dict[str, str]:
    """Liveness and database check, used by the deploy script before switching versions."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "error", "database": "unreachable"}
    return {"status": "ok", "database": "ok"}
