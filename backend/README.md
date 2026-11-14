# backend

API and server-side logic for the Styler store (products, categories, orders, settings).

Stack: Python 3.14, FastAPI, SQLAlchemy 2.1 (async with asyncpg), Alembic, Pydantic v2, pytest, managed with `uv`.

## Local development

Everything runs in Docker, so only Docker is needed on the machine. The dev compose file lives in `deploy/`. It needs `deploy/.env.dev` and the external `styler-net` network and `styler-db-data` volume, all created once per machine (see [`deploy/README.md`](../deploy/README.md#one-time-setup-on-each-machine)). Then, from the repository root:

```bash
# PostgreSQL on 127.0.0.1:5432, API on http://127.0.0.1:8000
docker compose --env-file deploy/.env.dev -f deploy/compose.dev.yaml up --build
curl http://127.0.0.1:8000/health                 # 200 {"status":"ok","database":"ok"}; 503 if the database is down
```

The `backend/` folder is mounted into the container and the API reloads on every save.

Checks (inside the running container):

```bash
docker compose --env-file deploy/.env.dev -f deploy/compose.dev.yaml exec api ruff check .
docker compose --env-file deploy/.env.dev -f deploy/compose.dev.yaml exec api ruff format --check .
docker compose --env-file deploy/.env.dev -f deploy/compose.dev.yaml exec api pytest
```

Dependencies are managed with `uv`; after editing `pyproject.toml`, refresh `uv.lock` and rebuild:

```bash
docker run --rm -u "$(id -u):$(id -g)" -e UV_CACHE_DIR=/tmp/uvc -v "$PWD/backend":/w -w /w ghcr.io/astral-sh/uv:0.9-python3.14-trixie-slim uv lock
```

### Docker image

`Dockerfile` is multi-stage, with two targets:

| Target | Used by | Contents |
|---|---|---|
| `dev` | `deploy/compose.dev.yaml` | all dependencies (including ruff and pytest), uvicorn with `--reload` |
| `prod` (default) | the deploy script (phase 6) | production dependencies, `app/` and the migrations (`alembic/`, `alembic.ini`) only, no uv, runs as a non-root user |

Dependencies are installed in their own stage from `pyproject.toml` and `uv.lock` only, with a uv cache mount, so a code change does not reinstall them and a dependency change reuses already-downloaded wheels.

## Structure

Feature-based: each feature keeps all its files in one folder. Every database table has its own model file inside the `models/` folder of the feature that owns it.

```
backend/
├── pyproject.toml
├── alembic.ini
├── Dockerfile
├── alembic/
│   ├── env.py                       # async; the URL comes from the app settings
│   ├── script.py.mako
│   └── versions/                    # one file per table (0001 … 0008), then 0009_seed_settings.py
├── app/
│   ├── main.py                      # creates the app, registers routers, /health
│   ├── core/                        # shared plumbing, no business logic
│   │   ├── config.py                # settings from environment variables only, all required (pydantic-settings)
│   │   ├── db.py                    # engine, session, Base (naming_convention), mixins, str_enum, soft-delete filter
│   │   ├── security.py              # argon2 and token generation
│   │   ├── rate_limit.py
│   │   └── errors.py
│   ├── shared/                      # types and rules used by more than one feature
│   │   ├── governorates.py          # the 12 governorates and their delivery zones
│   │   ├── money.py                 # Decimal with 3 places (JOD)
│   │   ├── phone.py                 # Jordanian phone pattern
│   │   ├── hex_color.py             # #rrggbb pattern
│   │   └── pricing_mode.py          # fixed / quote (products and the frozen order items)
│   ├── features/
│   │   ├── catalog/                 # categories and products
│   │   │   ├── enums.py             # BrandColor
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
│   │   │   ├── enums.py             # OrderStatus (done / cancelled)
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
    ├── conftest.py                  # rebuilds the test database with alembic upgrade head
    ├── test_migrations.py           # alembic check
    ├── test_schema_constraints.py   # CHECK constraints and enum values the check cannot see
    ├── core/                        # soft delete
    ├── catalog/
    ├── orders/
    └── settings/
```

## Database and migrations

### Tables

| Table | Model | Notes |
|---|---|---|
| `categories` | `catalog/models/category.py` | `color` is a logo color (`cyan`, `magenta`, `yellow`, `black`); names unique among live rows, ignoring case and surrounding spaces |
| `products` | `catalog/models/product.py` | `pricing_mode` `fixed` or `quote`; "available in colors" = has at least one color |
| `product_price_tiers` | `catalog/models/product_price_tier.py` | the same quantity may repeat with a different note (250 pcs · 4 cm, 250 pcs · 6 cm); only an exact duplicate is refused |
| `product_colors` | `catalog/models/product_color.py` | `hex` is lowercase `#rrggbb` |
| `orders` | `orders/models/order.py` | the order number is `id`, starting at **1001**; `status` is NULL, `done` or `cancelled` |
| `order_items` | `orders/models/order_item.py` | a frozen copy of the product; `unit_price` is NULL for a quote item until the manager prices it; line total = `unit_price × item_count` |
| `settings` | `settings/models/setting.py` | exactly one row: `id` defaults to 1 and a CHECK allows only 1; created by `0009_seed_settings.py` with the starting values |
| `admin_sessions` | `auth/models/admin_session.py` | only the SHA-256 of the session token is stored |

Conventions every table follows:

- **`id`** is an identity column; **`created_at`** and **`updated_at`** are set by the database.
- **Soft delete**: `deleted_at` on every table. Delete with `soft_delete(session, row)` from `app/core/db.py`, never `session.delete()`. ORM `SELECT`, `UPDATE` and `DELETE` statements skip deleted rows automatically; add `.execution_options(include_deleted=True)` to see them. `soft_delete()` also removes the row from the session, so `session.get()` cannot return it from memory. Unique rules are partial unique indexes `WHERE deleted_at IS NULL`, so a deleted name can be used again.
- **Database-generated values are fetched back** (`eager_defaults` on `Base`): `created_at` and `updated_at` are readable right after a flush, which async code needs.
- **Enums** are `VARCHAR` + `CHECK` (`str_enum` in `app/core/db.py`), not PostgreSQL `ENUM` types: adding a value is a plain constraint change.
- **Money** is `NUMERIC(10, 3)` (JOD with fils), never a float.
- **Images** are stored as the S3 key (`media/<uuid>.webp`), not a full URL.
- **Constraint names** come from the `naming_convention` on `Base.metadata` (`pk_`, `fk_`, `ix_`, `uq_`, `ck_`), so every migration can refer to them by a predictable name.
- **Rules are enforced in the database too**: the Jordanian phone pattern, positive quantities, non-negative prices, a `fixed` order item must have a quantity and a price.
- The 12 governorates and their delivery zones are a `StrEnum` in `app/shared/governorates.py`, not a table.

### Migration commands

Run inside the API container (`docker compose --env-file deploy/.env.dev -f deploy/compose.dev.yaml exec api ...`):

```bash
alembic upgrade head                                             # build or update the database
alembic revision --autogenerate --rev-id 0010 -m "short summary"  # draft a migration from model changes
alembic check                                                    # fails if a model changed without a migration
alembic upgrade head --sql                                       # print the SQL without running it
alembic downgrade -1                                             # local development only
```

Rules (also in the project decisions):

- **One migration per table.** Each table was created by its own file, with its own `upgrade` and `downgrade`, in foreign-key order:

  | File | Table |
  |---|---|
  | `0001_create_categories.py` | `categories` |
  | `0002_create_products.py` | `products` |
  | `0003_create_product_price_tiers.py` | `product_price_tiers` |
  | `0004_create_product_colors.py` | `product_colors` |
  | `0005_create_orders.py` | `orders` |
  | `0006_create_order_items.py` | `order_items` |
  | `0007_create_settings.py` | `settings` |
  | `0008_create_admin_sessions.py` | `admin_sessions` |
  | `0009_seed_settings.py` | the settings row (data, not structure) |

  A later change gets its own new file (`--rev-id 0010` and so on); a migration that already ran on the server is never edited. Generated files are formatted and linted by ruff automatically.
- **An autogenerated migration is a draft.** Read every line before committing: Alembic reads a rename as drop + add (data loss), and does not see changes to CHECK constraints or enum values.
- **Backward compatible (expand/contract)**: a new column is nullable or has a default; dropping or renaming a column takes two deploys.
- **Seed data is limited to the settings row** (`0009_seed_settings.py`), so the store has delivery fees and a WhatsApp number from the first start. Categories are entered by the manager. A data migration uses plain `sa.table(...)` definitions, never the app models, so it keeps working after the models change.
- `downgrade` is for local development only. On the server, a rollback restores the `pg_dump` taken before the migration.

### Tests and the database

Tests run against a real PostgreSQL database named by `TEST_DATABASE_URL` (`styler_test` on the same server as the dev database; its name must end in `_test`, or the tests refuse to start):

1. At the start of every run, the test database is dropped and rebuilt with `alembic upgrade head`, then downgraded to empty and upgraded again, so every migration and every downgrade runs.
2. `tests/test_migrations.py` runs `alembic check`, and `tests/test_schema_constraints.py` covers what it cannot see: CHECK constraint names, enum values and patterns (such as the phone regex) must match between the models and the database. A new enum value or a changed pattern without a migration fails here.
3. Each test gets a `db_session` inside a transaction that is rolled back afterwards, so tests never see each other's data.

## Configuration

The project is open source, so **no value lives in the code or in compose files**:

- `app/core/config.py` declares every setting with a type and **no default**. A missing or invalid value stops the app at startup with a validation error naming the setting.
- Values reach the container as environment variables from an env file passed by compose: `deploy/.env.dev` locally, the server's env file in production.
- Real env files are never committed (`.gitignore`). Each has a committed `.example` next to it with the variable names and empty values.
- A new setting is added in three places together: `config.py`, the `.example` file, and your own env file.

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
