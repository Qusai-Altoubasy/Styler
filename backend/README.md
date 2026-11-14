# backend

API and server-side logic for the Styler store (products, categories, orders, settings).

Stack: Python 3.14, FastAPI, SQLAlchemy 2.1 (async with asyncpg), Alembic, Pydantic v2, pytest, managed with `uv`.

## Structure

Feature-based: each feature keeps all its files in one folder. Every database table has its own model file inside the `models/` folder of the feature that owns it.

```
backend/
├── pyproject.toml
├── alembic.ini
├── Dockerfile
├── alembic/
│   ├── env.py
│   └── versions/
├── app/
│   ├── main.py                      # creates the app, registers routers, /health
│   ├── core/                        # shared plumbing, no business logic
│   │   ├── config.py                # settings from .env (pydantic-settings)
│   │   ├── db.py                    # engine, session, Base (naming_convention), SoftDeleteMixin
│   │   ├── security.py              # argon2 and token generation
│   │   ├── rate_limit.py
│   │   └── errors.py
│   ├── shared/                      # types and rules used by more than one feature
│   │   ├── governorates.py          # the 12 governorates and their delivery zones
│   │   ├── money.py                 # Decimal with 3 places (JOD)
│   │   └── phone.py                 # Jordanian phone validation
│   ├── features/
│   │   ├── catalog/                 # categories and products
│   │   │   ├── models/
│   │   │   │   ├── category.py              # categories
│   │   │   │   ├── product.py               # products
│   │   │   │   ├── product_price_tier.py    # product_price_tiers
│   │   │   │   └── product_color.py         # product_colors
│   │   │   ├── schemas.py
│   │   │   ├── service.py
│   │   │   ├── public_router.py     # /api/...
│   │   │   └── admin_router.py      # /api/admin/...
│   │   ├── orders/
│   │   │   ├── models/
│   │   │   │   ├── order.py                 # orders
│   │   │   │   └── order_item.py            # order_items
│   │   │   ├── schemas.py
│   │   │   ├── pricing.py           # totals and delivery, pure functions without the database
│   │   │   ├── service.py
│   │   │   ├── public_router.py
│   │   │   └── admin_router.py
│   │   ├── settings/
│   │   │   ├── models/
│   │   │   │   └── setting.py               # settings
│   │   │   ├── schemas.py
│   │   │   ├── service.py
│   │   │   ├── public_router.py
│   │   │   └── admin_router.py
│   │   ├── auth/                    # login, sessions, require_admin
│   │   │   ├── models/
│   │   │   │   └── admin_session.py         # admin_sessions
│   │   │   ├── schemas.py
│   │   │   ├── service.py
│   │   │   ├── dependencies.py      # require_admin
│   │   │   └── admin_router.py
│   │   └── media/                   # presigned POST, moving images from tmp/ to media/ (no tables)
│   │       ├── schemas.py
│   │       ├── service.py
│   │       └── admin_router.py
│   └── models.py                    # imports every model so Alembic sees them
├── cli/
│   └── set_password.py              # sets the manager password on the server
└── tests/
    ├── conftest.py                  # builds the database with alembic upgrade head
    ├── catalog/
    └── orders/
```

## Layers

| Layer | File | Role |
|---|---|---|
| Model | `models/<table>.py` | SQLAlchemy model: the table as stored |
| Schema (DTO) | `schemas.py` | Pydantic models for what enters and leaves the API: validation and the exact fields exposed |
| Service | `service.py` | Business logic, takes an `AsyncSession` |
| Router | `public_router.py`, `admin_router.py` | Endpoints: take a schema, call the service, return a schema |

Flow: router → service → models. No repository layer: the `AsyncSession` is enough at this size.

## Rules

- **One file per table**, named after the table in singular (`order_item.py` for `order_items`). Each feature's `models/__init__.py` exports its models.
- **Never return a model from an endpoint.** Every response goes through a schema, so a new column or a secret (`admin_password_hash`, `internal_note`) never leaks by accident.
- **Two routers per feature**: `public_router.py` under `/api` with no login, and `admin_router.py` under `/api/admin`, protected once at the router level with `Depends(require_admin)`. This matches the Caddy split between the two domains. The only open admin endpoint is login, on its own router inside `auth`.
- **Categories and products are one feature (`catalog`)** because they depend on each other (no deleting a category that has products; product count and lowest price on the category card).
- **Dependency direction**: `orders` uses `catalog` and `settings` only through their `service.py`. No feature imports from `orders`. `core` and `shared` import from no feature.
- **Soft delete everywhere**: every table has `deleted_at`. Queries exclude deleted rows by default, and unique constraints are partial (`WHERE deleted_at IS NULL`).

## Endpoints

| File | Endpoints |
|---|---|
| `catalog/public_router.py` | `GET /api/categories`, `GET /api/products`, `GET /api/products/{id}` |
| `catalog/admin_router.py` | `GET POST /api/admin/categories`, `PATCH DELETE /api/admin/categories/{id}`, `GET POST /api/admin/products`, `PATCH DELETE /api/admin/products/{id}` |
| `orders/public_router.py` | `POST /api/orders` |
| `orders/admin_router.py` | `GET /api/admin/orders`, `GET /api/admin/orders/stats`, `GET PATCH DELETE /api/admin/orders/{id}` |
| `settings/public_router.py` | `GET /api/settings` |
| `settings/admin_router.py` | `GET PATCH /api/admin/settings` |
| `auth/admin_router.py` | `POST /api/admin/login`, `POST /api/admin/logout`, `POST /api/admin/logout-all`, `POST /api/admin/password` |
| `media/admin_router.py` | `POST /api/admin/media/upload-url` |
| `main.py` | `GET /health` |
