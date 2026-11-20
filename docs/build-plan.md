# Styler website build plan

Order: backend first, then the frontend, then infrastructure and deployment. This way AWS costs only start once something is ready to run, and every phase is checked locally before the next one.

Each phase has a "done when" check: we don't move to the next phase until it passes.

---

## Technical choices

- **Backend**: Python 3.14, FastAPI, SQLAlchemy 2.1 (async with asyncpg), Alembic for migrations, Pydantic v2, pytest. Packages managed with `uv`. (Decided 2026-11-14: 3.14 instead of 3.15 because some libraries may not support 3.15 yet; async because it fits FastAPI best.)
- **Frontend**: Vite, React, TypeScript, React Router, TanStack Query, an i18n library for Arabic and English.
- **Manager login**: one password stored as an argon2 hash in the `settings` table, and a cookie session (HttpOnly, Secure, SameSite=Strict) bound to the admin domain only, lasting 30 days. Sessions live in the `admin_sessions` table so a password change or a logout (which always logs out every device) revokes them all. Forgotten password: a CLI script on the server that Qusai runs.

## Storefront and admin separation

Two separate apps in the same repository, with no link between them:

| | Storefront | Admin dashboard |
|---|---|---|
| Address | Main domain | `admin.<domain>` |
| Code | `frontend/storefront/` | `frontend/admin/` |
| API | Public `/api/*` | `/api/admin/*` |

- Shared code (API types, brand colors, shared translations) lives in `frontend/shared/`.
- Each app has its own bucket and CloudFront distribution, with the same server behind both.
- Customers never download the admin code, and the manager's session is never sent with storefront requests.

The code structure (feature-based, one model file per table) is documented in `backend/README.md` and `frontend/README.md`.

---

## Phase 0: Foundation

- Folder structure inside `backend/`, with linting and formatting (ruff).
- The `frontend/` structure and its tools (eslint, prettier) are deferred to phase 3 (decided 2026-11-14).
- `docker compose` for local development: PostgreSQL and FastAPI, talking over the external `styler-net` network, with the database on the external `styler-db-data` volume (both created once by hand, see `deploy/README.md`).
- No configuration values in code or compose files (the project is open source): every value comes from an env file. Real env files are never committed; each has a committed `.example` with the variable names and empty values (`deploy/.env.dev.example` for local development). A `.gitignore` for the project.
- A `/health` endpoint in the backend.

**Done when:** one command starts the backend and the database locally, and `/health` returns 200.

## Phase 1: Data model

Tables:

- `categories`: Arabic and English name, color, optional image, sort order.
- `products`: name and description in both languages, category (required), image, pricing mode (`fixed` or `quote`), free delivery, visible/hidden.
- `product_price_tiers`: quantity, price, note in both languages (for `fixed` products).
- `product_colors`: name in both languages and a hex value.
- `orders`: the order number is the `id` itself, name, phone, governorate, address, delivery fee, subtotal, total, internal note, the `status` mark (empty, `done` or `cancelled`), date.
- `order_items`: a **frozen copy** of the product name, quantity, color and price at order time, so an old order never changes when the product is edited or deleted. Plus a field for the quote price that the manager fills in.
- `settings`: the two zone fees, WhatsApp number, Instagram and Facebook links, the manager password hash.
- `admin_sessions`: the manager's open sessions and their expiry.

Requirements:

- Alembic migrations, with a fixed `naming_convention` from the first migration: one migration file per table, each with its own `upgrade` and `downgrade`.
- Tests build the database with `alembic upgrade head`, and run `alembic check` so no model change slips through without a migration.
- Seed data: only the settings row, in its own migration (`0009_seed_settings.py`): 2 and 3 JOD, the store's WhatsApp, Instagram and Facebook. The manager enters the categories.
- The 12 governorates and their zones are fixed in code (enum), not a table.
- **Soft delete in every table** (decided 2026-11-14): a nullable `deleted_at` column in every table; deleting fills it instead of removing the row. All queries exclude deleted rows by default, and unique constraints become partial (`WHERE deleted_at IS NULL`).

Decided while building (2026-11-14):

- Enums are `VARCHAR` + `CHECK`, not PostgreSQL `ENUM` types.
- Order numbers (the `id`) start at 1001.
- `settings` is a single row with typed columns (`id = 1`), not a key/value table.
- Images are stored as the S3 key, and the URL is built from settings.
- A product is "available in colors" when it has at least one color (no separate flag).
- An order item has one `unit_price`: taken from the tier for `fixed`, set by the manager for `quote`.
- Tests use a separate `styler_test` database on the same PostgreSQL server.

**Done when:** an empty database is built completely with one command, including the settings row.

## Phase 2: API

**For customers (no login):**

- Visible categories with product count and lowest price.
- Products with filters (category, search, price from/to, pricing mode, free delivery) and sorting.
- Product details.
- Public settings (delivery fees, contact links).
- Create an order: validate the phone (`^07[789]\d{7}$`), **recalculate prices and delivery on the server** (never trust the browser's numbers), and generate the order number (the `id`).

**For the manager (after login):**

- Login, logout (always every device), and password change.
- Categories: add, edit, delete (refused if it has products).
- Products: add, edit, hide/show, delete, with the quantity table and colors.
- Image upload link (presigned POST), and moving the image from `tmp/` to `media/` on save.
- Orders: quick stats, the list with search, details, editing the quote price (with `subtotal` and `total` recalculated automatically), the internal note and the mark (done/cancelled), filter by mark, delete.
- Settings: read and edit.

**Protection:**

- Rate limits on login and on order creation.
- For local development: MinIO instead of S3, so uploads can be tested without an AWS account.

**Done when:** pytest tests against a real database cover: totals and delivery (fixed, quote, mixed, free delivery), phone validation, refusing to delete a category with products, old orders staying unchanged after a product edit, cancelled orders excluded from the orders value, and all sessions revoked on password change.

## Phase 3: Customer storefront

- Basics: routing, both languages with RTL/LTR, dark and light mode, header and footer.
- Home page and category cards.
- Products page: filters, chips, sorting, and collapsible filters on mobile.
- Product page: quantity, color, number of items.
- Cart (stored in `localStorage`).
- Order form, the ready-made WhatsApp message, and the "we got your order" page with a resend button.

**Done when:** a full order from a phone (fixed, quote, and mixed) reaches the database and opens WhatsApp with the right message, in both languages and both modes.

Decided while building (2026-11-16):

- The look is designed fresh around offset printing (CMYK inks, crop marks, registration), not copied from the MVP. Animations use Motion and respect the device's reduced-motion setting.
- The WhatsApp message follows the page language (Arabic or English). Its numbers come from the server's confirmation, not the cart.
- The "we got your order" page renders from the confirmation saved in the browser, since there is no public endpoint to read an order back.
- The first quantity and the first color are preselected on the product page.
- Fonts are served from the app (fontsource), with no request to Google.
- pnpm runs through corepack. TypeScript is pinned to 6.0.x until typescript-eslint supports 7.

## Phase 4: Admin dashboard

- A standalone app in `frontend/admin/`, with `noindex` and "add to home screen" settings (name and icon).
- Login page.
- Products tab: categories section on top, products below, with image upload and in-browser resizing.
- Settings tab, with password change and the logout button (logs out every device).
- Orders tab: quick stats, table, search, details, the mark (done/cancelled) and its filter, the customer's WhatsApp button.
- A second confirmation for every delete.

**Done when:** the manager adds a category and a product with an image, colors and prices from their phone without help.

## Phase 5: Infrastructure (CDK)

This is where costs start, and where the domain is bought.

- AWS account: MFA on root, an IAM user for Qusai, and a budget alert at 10 USD.
- Storage stack: a bucket for the storefront, a bucket for the admin dashboard, a bucket for images (with `tmp/`, lifecycle, and CORS for uploads from the admin domain only), a bucket for backups (30-day lifecycle).
- Server stack: Lightsail, static IP, firewall (443 for the world, 22 for Qusai's IP), and a least-privilege IAM user for the server.
- Frontend stack: a storefront distribution (`/*`, `/media/*`, `/api/*`) and an admin distribution (`/*`, `/media/*`, `/api/admin/*`), one ACM certificate for both names, and the secret header for the server.
- Domain and DNS on Cloudflare (outside CDK, DNS only mode): buy the domain, then add the ACM validation records, then the main domain and `admin` records pointing to CloudFront, and a record for the server address.

**Done when:** `cdk deploy` builds everything from scratch, both domains open a test page over HTTPS, and `/api/admin/*` is refused from the storefront domain.

## Phase 6: Deployment

- One-time server setup: create the external `styler-net` network and `styler-db-data` volume, the same as on Qusai's machine.
- A backend `Dockerfile`, `compose.prod.yaml` (using the same external network and volume), and a `Caddyfile` (checking the secret header, and refusing `/api/admin/*` from anything but the admin domain).
- Deploy script: check the commit, build, upload over SSH, `pg_dump`, `alembic upgrade head` as its own step (if it fails, the script stops and the old version keeps running), start, check `/health`, automatic rollback on failure, and keep the last two images.
- Frontend deploy script: build, `s3 sync`, invalidation. Runs for each app separately (storefront or admin).
- Nightly backup (cron on the server) to S3.
- **Actually restore** a backup, not just take one.

**Done when:** deploy a version, then deploy a deliberately broken version and confirm the automatic rollback worked, then restore the database from an S3 backup.

## Phase 7: Launch

- The manager enters the real products, prices and images.
- A full check on real phones (Android and iPhone) and on real WhatsApp.
- Change the manager password and hand it over.
- A short guide for the manager: how to add a product, and how to review orders.
- Review the AWS bill after the first week and the first month.

---

## Out of scope for now

Any payment on the site, customer accounts, OTP, coupons, a tracking page, full order statuses, multiple admin accounts, CI/CD, and automatic notifications to the manager.
