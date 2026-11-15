# backend

API and server-side logic for the Styler store (products, categories, orders, settings).

Stack: Python 3.14, FastAPI, SQLAlchemy 2.1 (async with asyncpg), Alembic, Pydantic v2, pytest, ruff and mypy, managed with `uv`.

## Local development

Everything runs in Docker, so only Docker is needed on the machine. The dev compose file lives in `deploy/`. It needs `deploy/.env.dev` and the external `styler-net` network and `styler-db-data` volume, all created once per machine (see [`deploy/README.md`](../deploy/README.md#one-time-setup-on-each-machine)). Then, from the repository root:

```bash
# PostgreSQL on 127.0.0.1:5432, MinIO on 127.0.0.1:9000 (console :9001), API on http://127.0.0.1:8000
docker compose --env-file deploy/.env.dev -f deploy/compose.dev.yaml up --build
curl http://127.0.0.1:8000/health                 # 200 {"status":"ok","database":"ok"}; 503 if the database is down
```

The `backend/` folder is mounted into the container and the API reloads on every save.

Checks (inside the running container):

```bash
docker compose --env-file deploy/.env.dev -f deploy/compose.dev.yaml exec api ruff check .
docker compose --env-file deploy/.env.dev -f deploy/compose.dev.yaml exec api ruff format --check .
docker compose --env-file deploy/.env.dev -f deploy/compose.dev.yaml exec api mypy
docker compose --env-file deploy/.env.dev -f deploy/compose.dev.yaml exec api pytest
```

`mypy` runs in strict mode with the Pydantic plugin over `app/`, `alembic/` and `tests/` (settings in `pyproject.toml`).

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
│   │   ├── security.py              # argon2 (one hash at a time) and session tokens
│   │   ├── rate_limit.py            # in-memory limiter: N attempts per window per key
│   │   ├── client_ip.py             # the caller's rate-limit key (CDN header, IPv6 /64)
│   │   ├── storage.py               # S3 clients (MinIO locally) and the missing / access-denied error checks
│   │   └── errors.py                # AppError with a code, and its JSON handler
│   ├── shared/                      # types and rules used by more than one feature
│   │   ├── governorates.py          # the 12 governorates and their delivery zones
│   │   ├── money.py                 # MONEY column type, MoneyIn (non-negative, 3 places), MAX_AMOUNT
│   │   ├── patch.py                 # PatchModel: PATCH bodies, null only where NULLABLE
│   │   ├── phone.py                 # Jordanian phone pattern, normalization, 962 form
│   │   ├── hex_color.py             # #rrggbb pattern
│   │   ├── ids.py                   # DbId / PathId: ids bounded to the int4 range
│   │   ├── text.py                  # NoControlCharacters for every free-text field, SearchText
│   │   ├── media.py                 # image key -> /media/... link
│   │   ├── text_search.py           # ILIKE patterns with % and _ escaped
│   │   └── pricing_mode.py          # fixed / quote (products and the frozen order items)
│   ├── features/
│   │   ├── catalog/                 # categories and products
│   │   │   ├── enums.py             # BrandColor
│   │   │   ├── models/
│   │   │   │   ├── category.py              # categories
│   │   │   │   ├── product.py               # products
│   │   │   │   ├── product_price_tier.py    # product_price_tiers
│   │   │   │   └── product_color.py         # product_colors
│   │   │   ├── schemas.py           # the storefront's
│   │   │   ├── service.py           # the storefront's queries
│   │   │   ├── admin_schemas.py     # the dashboard's
│   │   │   ├── admin_service.py     # the dashboard's reads and writes
│   │   │   ├── row_replacement.py   # replacing tiers and colors by id, pure
│   │   │   ├── public_router.py     # /api/...
│   │   │   └── admin_router.py      # /api/admin/...
│   │   ├── orders/
│   │   │   ├── enums.py             # OrderStatus (done / cancelled)
│   │   │   ├── models/
│   │   │   │   ├── order.py                 # orders
│   │   │   │   └── order_item.py            # order_items
│   │   │   ├── schemas.py
│   │   │   ├── pricing.py           # totals and delivery, pure functions without the database
│   │   │   ├── item_rules.py        # what may be ordered for one product (tier, color), pure
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
│   │   │   ├── cookies.py           # the session cookie and its flags
│   │   │   ├── dependencies.py      # require_admin
│   │   │   └── admin_router.py
│   │   └── media/                   # presigned POST, moving images from tmp/ to media/ (no tables)
│   │       ├── keys.py              # the tmp/<uuid>.webp and media/<uuid>.webp shapes, pure
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
    ├── media/                       # against the real MinIO, in the TEST_S3_BUCKET bucket
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

The media tests use the real MinIO container too, in their own bucket named by `TEST_S3_BUCKET` (its name must end in `-test`). The bucket is created if missing and emptied before every media test. The upload links are signed for the browser's address (`127.0.0.1:9000`), which is not MinIO from inside the container, so the tests send the same form to `S3_ENDPOINT_URL`: a POST policy's signature covers the policy, not the host.

## Configuration

The project is open source, so **no value lives in the code or in compose files**:

- `app/core/config.py` declares every setting with a type and **no default**. A missing or invalid value stops the app at startup with a validation error naming the setting.
- Values reach the container as environment variables from an env file passed by compose: `deploy/.env.dev` locally, the server's env file in production.
- Real env files are never committed (`.gitignore`). Each has a committed `.example` next to it with the variable names and empty values.
- A new setting is added in three places together: `config.py`, the `.example` file, and your own env file.
- Validation errors name the setting but never print its value (`hide_input_in_errors`), since values hold passwords and keys.

Image storage settings:

| Setting | Production | Local |
|---|---|---|
| `S3_BUCKET` | the images bucket | `styler-images` in MinIO |
| `S3_REGION` | `eu-west-1` | the same (MinIO answers as `MINIO_SITE_REGION`) |
| `S3_ENDPOINT_URL` | empty (real S3) | `http://minio:9000`: where the API reaches MinIO on `styler-net` |
| `S3_PUBLIC_ENDPOINT_URL` | empty (real S3) | `http://127.0.0.1:9000`: where the browser uploads; the service name means nothing outside Docker |
| `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY` | the server's IAM key | MinIO's root user and password |

The two endpoints are both empty or both set; anything else stops the app at startup.

## Layers

| Layer | File | Role |
|---|---|---|
| Model | `models/<table>.py` | SQLAlchemy model: the table as stored |
| Schema (DTO) | `schemas.py` | Pydantic models for what enters and leaves the API: validation and the exact fields exposed |
| Service | `service.py` | Business logic, takes an `AsyncSession` |
| Router | `public_router.py`, `admin_router.py` | Endpoints: take a schema, call the service, return a schema |

Flow: router → service → models. No repository layer: the `AsyncSession` is enough at this size.

A feature may split the dashboard's side into `admin_schemas.py` and `admin_service.py` when the files grow large (as `catalog` does), with the same layer rules.

- **A router only speaks HTTP**: it takes a schema, calls one service function, and returns a schema built with that schema's own `from_<model>()` class method. No queries and no business rules in a router.
- **A service function reads as a list of steps** at one level of detail; each step is a small private function with one job (load, check, compute, save).
- **Rules that need no database are pure functions** in their own module (`orders/pricing.py`, `orders/item_rules.py`), tested without a database. Services wire them to the database.
- **Services return models or named results** (`NamedTuple`), never anonymous tuples.

## Rules

- **One file per table**, named after the table in singular (`order_item.py` for `order_items`). Each feature's `models/__init__.py` exports its models.
- **Never return a model from an endpoint.** Every response goes through a schema, so a new column or a secret (`admin_password_hash`, `internal_note`) never leaks by accident.
- **Two routers per feature**: `public_router.py` under `/api` with no login, and `admin_router.py` under `/api/admin`, protected once at the router level with `Depends(require_admin)`. This matches the Caddy split between the two domains. The only open admin endpoints are login and logout, on their own router inside `auth` (logout ends sessions only when its cookie belongs to a live one).
- **Categories and products are one feature (`catalog`)** because they depend on each other (no deleting a category that has products; product count and lowest price on the category card).
- **Dependency direction**: `orders` calls `catalog` and `settings` only through their `service.py` (it never queries their tables itself); it may use their model types, such as the `Product` a service returned. No feature imports from `orders`. `core` and `shared` import from no feature.
- **Soft delete everywhere**: every table has `deleted_at`. Queries exclude deleted rows by default, and unique constraints are partial (`WHERE deleted_at IS NULL`).

## API conventions

- **Errors** from business rules have one shape, with a stable `code` the bilingual frontends translate:

  ```json
  {"error": {"code": "color_required", "message": "Choose a color", "details": {"item_index": 0, "product_id": 7}}}
  ```

  `404` not found, `409` conflict (a duplicate name, a category that still has products), `422` a broken rule. Malformed requests (wrong types, a bad phone number) keep FastAPI's standard `422` body with `detail`.
- **Input types**: every id in a request is a `DbId` (body, query) or `PathId` (URL), bounded to the int4 range; every free-text field adds `NoControlCharacters`. Out-of-range ids and NUL characters are a `422`, never a database error.
- **Money** is sent as a string with 3 decimal places (`"7.000"`), never a float.
- **A product's price** is the lowest price in its quantity table, the same number on the category card, the price filter and the price sort. Quote products have no price, even if they still have tier rows, and sort last in both directions.
- **Shown in the store** means visible and orderable: a `fixed` product without a live tier is left out of every public query, like a hidden one.
- **Images** are returned as `image_url`, a path (`/media/<uuid>.webp`) on the same domain as the app.
- **Orders**: the browser sends only the choices (product, tier, color, approximate quantity, item count). Unknown fields such as a price are refused with `422`; the server computes every price, the delivery fee and the totals (`orders/pricing.py`).
- **Transactions**: a service that writes commits its own work; reads never commit.

## Manager login

- **One password**, stored as an argon2 hash in the settings row; no username. Set it the first time, or when it is forgotten, on the server (it asks twice and never takes the password as an argument):

  ```bash
  docker compose --env-file deploy/.env.dev -f deploy/compose.dev.yaml exec -it api python -m cli.set_password
  ```

  Setting it logs every device out. Until it is set, login answers `409 password_not_set` (not counted toward the limit), so a missed first-deploy step is obvious.
- **Sessions**: login returns `204` with the `styler_admin_session` cookie (HttpOnly, Secure, SameSite=Strict, `Path=/api/admin`, 30 days). The database stores only the token's SHA-256. `GET /api/admin/session` answers `200` while logged in and `401` otherwise, which is how the dashboard decides to show the login page.
- **Password change** needs the current password, ends every session, and sets a fresh cookie on the device that changed it. **Logout** ends every session on every device, this one included: there is one logout, which is also what to press when the phone is lost. It is open, so a device whose session already ended can still clear its cookie; with no live session it ends nothing. Expired sessions are ended at the next login.
- **Rate limits** (in memory, so one worker only; a restart resets them):
  - wrong passwords (login and password change): 5 per 15 minutes per IP;
  - orders: 10 per 3 minutes per IP, generous because of mobile CGNAT.

  A blocked request gets `429` with `Retry-After`. The IP comes from the header named by `CLIENT_IP_HEADER` (`CloudFront-Viewer-Address` behind CloudFront; empty locally, where the connection's own address is used). IPv6 is keyed by its /64.

## Images

The manager's browser uploads straight to the bucket; the API only signs the upload and later moves the file. Nothing passes through the server.

1. The dashboard resizes the image and converts it to WebP, then calls `POST /api/admin/media/upload-url` with `{"content_type": "image/webp"}`. The answer is a presigned POST: `url`, form `fields`, the `key` (`tmp/<uuid>.webp`, generated by the server), `max_bytes` and `expires_in_seconds`.
2. The browser posts the form fields, then the image as `file`, to `url`. The signed policy fixes the key, the content type (`image/webp` only) and the size (1 byte to 2 MiB), and expires after 5 minutes. S3 refuses anything else (`403`, or `400 EntityTooLarge`). Only the declared type and size are checked, not the bytes themselves: there is no image processing on the server.
3. The dashboard sends the key with the product or category. Before committing, the catalog calls `media.service.save_image(key)`, which moves `tmp/<uuid>.webp` to `media/<uuid>.webp` and returns the key to store. A `media/` key (an edit that keeps the image) comes back unchanged. Any other shape is `422 invalid_image_key`; a `tmp/` upload that does not exist (never finished, or older than a day) is `422 image_not_uploaded`.
4. When an image is replaced or removed, the catalog calls `media.service.delete_image(old_key)` after its commit. Uploads that are never saved are deleted by the bucket's `tmp/` lifecycle rule after one day.

**The server key's permissions.** The key in the server's env file (`S3_ACCESS_KEY_ID`) needs exactly this on the images bucket (the backups folder is separate):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:ListBucket"],
      "Resource": "arn:aws:s3:::<images bucket>"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
      "Resource": [
        "arn:aws:s3:::<images bucket>/tmp/*",
        "arn:aws:s3:::<images bucket>/media/*"
      ]
    }
  ]
}
```

`s3:ListBucket` is not optional: without it, S3 answers `403 AccessDenied` instead of `404` for an object that does not exist, so an expired upload could not be told apart from a broken key. The service never reads a denial as "missing": any `403` from the storage is logged at error level with the operation, the object and the permissions above, and the request fails with `500 storage_misconfigured`. It is `500`, not `503`, because retrying does not help until the key is fixed. Locally, MinIO's root key hides this, and MinIO answers `404` for a missing object even without `ListBucket`. So `tests/media/test_storage_permissions.py` checks the policy on MinIO with a key that holds only this policy, and checks the `403` answers with stubbed responses.

Saved images get `Cache-Control: public, max-age=31536000, immutable`: a new image always has a new key. The browser loads them at `/media/<uuid>.webp` on its own domain (`app/shared/media.py`); presigned links are for upload only.

Locally, MinIO allows uploads from the origins in `MINIO_API_CORS_ALLOW_ORIGIN` (the dashboard's dev server), and the `storage-init` service makes `media/` readable so the dev server can proxy `/media/*` to `http://127.0.0.1:9000/<S3_BUCKET>/media/*`. See [`deploy/README.md`](../deploy/README.md#minio-local-image-storage).

## Catalog in the dashboard

- **Categories**: the list has every live category, also those without products, with `product_count` counting every live product (hidden ones too). A name already used by a live category, ignoring case and surrounding spaces, is `409 category_name_taken` with the clashing `field`; a deleted category's name is free again. Deleting a category that still has a live product is `409 category_has_products` (move or delete them first).
- **Products**: the list is paged like the orders log (`{"items", "total", "limit", "offset"}`, `limit` 1–100, default 50) and has every live product, hidden ones included, newest first, each with its whole quantity table, colors and image key, so the edit form needs no extra request (filters: `category_id`, `q`, `is_visible`). `shown_in_store` says whether customers see it, by the same rule as the storefront's queries (`Product.is_shown_in_store()` and its SQL twin `Product.shown_in_store()`). A `PATCH` changes only the fields it carries (`is_visible` hides and shows); `null` is refused except for `image_key`. An unknown or deleted category is `422 category_not_found`.
- **Tiers and colors** are sent as whole lists that replace the current ones. A row with the `id` of a live row of the same product updates it in place and keeps its id, so carts in the storefront keep working after a price change; a row without `id` is new; live rows left out are soft-deleted. An id of another product is `422 price_tier_not_found` / `color_not_found`, and an exact duplicate tier (same quantity and notes; an empty note is null) is `422 duplicate_price_tier` (`409` with the same code when two overlapping saves add the same tier and only the unique index sees it). Colors keep the order they were sent in. A tier that takes the quantity and note another kept tier has now (two tiers swapping) is saved as a new row with a new id, so the unique index never clashes on the way.
- **Images**: `image_key` is a `tmp/` key from the upload link, the row's current `media/` key (keep it), or `null` (remove it). Any other `media/` key is `422 invalid_image_key`, and an upload whose image already belongs to another row, live or deleted (the same upload sent twice, or a `tmp/` key built from another row's image), is `422 image_in_use`: two rows sharing one object would lose it when either replaced its image. A retried save still works. The upload is moved only after every other check passed; if the save then fails, the moved image is deleted again (never the row's previous one). The replaced image is deleted after the commit, and if that delete fails it is logged and the old image is left behind, while the save still succeeds. Deleting a product or category keeps its image.
- **Old orders never change**: an order item is a frozen copy (names, tier, color, price), so editing or deleting a product leaves every order as it was.

## Order log

The dashboard's Orders tab (`orders/admin_router.py`). Soft-deleted orders appear nowhere.

- **List** `GET /api/admin/orders?status=&q=&limit=&offset=`: newest first, `{"items": [...], "total", "limit", "offset"}`. `limit` is 1 to 100 (default 50). Each row has the order number (`id`), date, customer, phone, governorate, `products` (both names and the count of each line), `total`, `status` and `awaiting_quote`.
  - `status`: `all` (default), `unmarked`, `done` or `cancelled`.
  - `q` searches the customer's name (ignoring case) always, and, when it is a number, the phone (any part, as typed: Arabic digits, spaces, dashes, `+962 7…`) and the order number. A number too large for an id only searches the phone.
- **Stats** `GET /api/admin/orders/stats`: `all_orders`, `today_orders`, `quote_orders` and `orders_value`.
  - The three counts include cancelled orders; `orders_value` (the sum of `total`) leaves them out.
  - "Today" is the calendar day in Jordan, computed by PostgreSQL (`AT TIME ZONE 'Asia/Amman'`).
  - `quote_orders` counts orders that contain any quote item, priced or not (cancelled ones included, like the other counts). Whether an order still waits for a price is the `awaiting_quote` flag on each row.
- **Details** `GET /api/admin/orders/{id}`: the customer, `whatsapp_number` (`9627XXXXXXXX` for the chat link), the frozen items with their line totals, delivery fee, subtotal, total, `internal_note` and `status`.
- **Edit** `PATCH /api/admin/orders/{id}`: only the fields sent change.
  - `status`: `done`, `cancelled`, or `null` to clear the mark. It never sends anything and never reaches the customer.
  - `internal_note`: text, or `null` / `""` to clear it.
  - `item_prices`: `[{"item_id": 12, "unit_price": "4.500"}]`, or `"unit_price": null` to clear a price. Only quote items of this order (`422 item_price_fixed`, `422 order_item_not_found`). `subtotal` and `total` are then recalculated with `orders/pricing.py`, keeping the delivery fee stored on the order; unpriced items count as zero.
  - Edit and delete lock the order row (`SELECT ... FOR UPDATE`) until they commit, so two overlapping edits of one order run one after the other and the totals always include every saved price. Reads take no lock.
- **Delete** `DELETE /api/admin/orders/{id}`: soft-deletes the order and its items (`204`). Unknown ids are `404 order_not_found`.

## Endpoints

| File | Endpoints |
|---|---|
| `catalog/public_router.py` | `GET /api/categories`, `GET /api/products`, `GET /api/products/{id}` |
| `catalog/admin_router.py` | `GET POST /api/admin/categories`, `PATCH DELETE /api/admin/categories/{id}`, `GET POST /api/admin/products`, `PATCH DELETE /api/admin/products/{id}` |
| `orders/public_router.py` | `POST /api/orders` |
| `orders/admin_router.py` | `GET /api/admin/orders`, `GET /api/admin/orders/stats`, `GET PATCH DELETE /api/admin/orders/{id}` |
| `settings/public_router.py` | `GET /api/settings` |
| `settings/admin_router.py` | `GET PATCH /api/admin/settings` |
| `auth/admin_router.py` | `POST /api/admin/login`, `GET /api/admin/session`, `POST /api/admin/logout`, `POST /api/admin/password` |
| `media/admin_router.py` | `POST /api/admin/media/upload-url` |
| `main.py` | `GET /health` |
