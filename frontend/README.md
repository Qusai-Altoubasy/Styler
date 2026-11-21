# frontend

The customer storefront (phase 3) and the manager dashboard (phase 4), two separate apps. The prototype in ../mvp is a suggested look, not a binding spec.

Stack: Vite, React 19, TypeScript (strict), React Router, TanStack Query, i18next for Arabic (RTL) and English (LTR), Motion for animations, pnpm workspaces, eslint, prettier, vitest.

## Local development

pnpm runs through corepack (bundled with Node), pinned by `packageManager` in `package.json`, so nothing is installed globally.

```bash
cd frontend
corepack pnpm install
cp storefront/.env.example storefront/.env   # then fill in the two proxy targets
cp admin/.env.example admin/.env             # the same two targets
corepack pnpm --dir storefront dev           # http://localhost:5173
corepack pnpm --dir admin dev                # http://localhost:5174
```

The backend must be running (`deploy/compose.dev.yaml`). The dev server proxies `/api/*` to the api container and `/media/*` to MinIO, so the app talks to the API on its own origin, as it will behind CloudFront. Both targets come from each app's `.env` with no defaults: a missing value stops the dev server. The dashboard uploads images straight to MinIO, so its address must be in `MINIO_API_CORS_ALLOW_ORIGIN` (`deploy/.env.dev`). To log in locally, set a password once with `cli.set_password` (see `backend/README.md`).

| Command (from `frontend/`)             | What it does                                                                                                                                       |
| -------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| `corepack pnpm gen:api`                | Regenerates `shared/api/schema.d.ts` from the running api container's OpenAPI                                                                      |
| `corepack pnpm typecheck`              | `tsc` over every package                                                                                                                           |
| `corepack pnpm lint`                   | eslint (typescript-eslint strict, React hooks rules)                                                                                               |
| `corepack pnpm format`                 | prettier                                                                                                                                           |
| `corepack pnpm test`                   | vitest: pricing, cart checks, filters, phone, money and the WhatsApp message; the dashboard's product and settings forms, numbers and image sizing |
| `corepack pnpm --dir storefront build` | Production build into `storefront/dist`                                                                                                            |
| `corepack pnpm --dir admin build`      | Production build into `admin/dist`                                                                                                                 |

TypeScript is pinned to 6.0.x because typescript-eslint does not support 7 yet.

## Structure

Two separate apps with no link between them, plus shared code. Inside each app the code is feature-based.

```
frontend/
├── package.json                     # pnpm workspaces, root scripts
├── shared/                          # @styler/shared
│   ├── api/                         # generated schema.d.ts, type aliases, the fetch client and ApiError
│   ├── i18n/                        # i18next setup, RTL/LTR, pick() for _ar/_en fields
│   ├── theme/                       # design tokens (theme.css), light/dark following the device
│   ├── ui/                          # ui.css: buttons, fields and tags both apps use
│   └── utils/                       # money in fils, phone, digits, governorate names
├── storefront/src/                  # main domain, talks to /api/*
│   ├── app/                         # router, layout, header, footer, common strings
│   ├── lib/                         # state more than one feature needs: cart, totals, settings, categories
│   ├── ui/                          # small storefront components: image frame, stepper, bottom sheet, icons
│   └── features/
│       ├── catalog/                 # home, product list, filters
│       ├── product/                 # product page
│       ├── cart/                    # cart page
│       └── checkout/                # form, WhatsApp message, "we got your order"
└── admin/src/                       # admin.<domain>, talks to /api/admin/*
    ├── app/                         # router, layout with the tabs, session gate, common strings and error texts
    ├── lib/                         # session (login, logout, password), errors, numbers, dates, image resizing and upload
    ├── ui/                          # small controls: two-tap delete, switch, segmented choice, image picker, fields
    └── features/
        ├── auth/                    # login page
        ├── catalog/                 # Products tab: categories, products, the product form (tiers, colors)
        ├── settings/                # Settings tab: fees, contact links, password, logout
        └── orders/                  # Orders tab: stats, log, order page
```

## Rules

- Each feature holds its components, its `api.ts` (TanStack Query hooks) and its own translation strings (`i18n.ts`, one i18next namespace per feature).
- A feature never imports from inside another feature. What more than one feature needs goes to the app's `lib/` or `ui/`, or to `shared/` when both apps need it.
- API types are generated, never written by hand, so a backend change breaks the build until the frontend is fixed.
- Totals in the cart are for display only. The server recalculates every order and is the source of truth. Money is added up in integer fils (`shared/utils/money.ts`), never as floats.
- Every typed number goes through `toAsciiDigits` first, so Arabic-Indic digits work everywhere (phone, quantities, prices).

## Storefront behavior

- **Language and theme**: Arabic by default, saved in `localStorage`. The theme follows the device until the customer switches it. An inline script in `index.html` applies both before the first paint, so nothing flashes.
- **Filters live in the URL** (`/products?category=3&min=2&sort=price_asc`), so category cards link in and the back button works. On phones they fold into a bottom sheet behind a "Filters (n)" button, and active filters show as removable chips.
- **Cart** (`lib/cart.ts`): `localStorage`, at most 50 lines and 10,000 items per line (the API's caps). Each line keeps the customer's choices plus a snapshot for display. The cart and checkout re-read every product (`lib/resolvedCart.ts`), so a hidden or deleted product, a removed quantity or color, or a switch to quote pricing shows as unavailable and blocks checkout until it is removed.
- **Product page**: the first quantity and the first color are preselected, so the customer is never blocked.
- **Order**: the request sends only the choices. After the server confirms, the confirmation is saved in `sessionStorage` (`styler.lastOrder`: it holds the customer's name, phone and address, so it lives only as long as the tab), the cart is cleared, and the "we got your order" page opens. About a second later it opens WhatsApp with a ready message. The page renders from the saved confirmation, so a refresh or coming back from WhatsApp shows it again without opening WhatsApp twice. The resend button is a plain link.
- **The WhatsApp message follows the page language** (Arabic or English; an English field the manager left empty falls back to Arabic). Every number in it comes from the server's confirmation, and it never mentions payment.
- **Errors**: item errors from the API (`product_unavailable`, `color_not_found`, …) refresh the products and point to the cart; a `429` shows how long to wait, from `Retry-After`.

## Look and motion

The design is built around offset printing, not the MVP:

- The palette is the logo's CMYK inks on a cool paper white. Dark mode prints on the brand black (`#16171b`).
- Readex Pro for headings and IBM Plex Sans Arabic for text, served from the app (fontsource), not from Google.
- The home heading inks in: each word rises out of a soft blur while a cyan-magenta-yellow band rolls across it in reading direction (right to left in Arabic), then it rests in solid ink. It plays once per visit.
- Images sit in frames with crop marks. Products without an image show a halftone pattern in their category's ink.
- Category cards fade up one after another. On hover they lift a little with a soft glow in their category's ink while the image eases closer; no springs or hard offsets.
- Other motion answers the customer's actions: the cart badge pops, add-to-cart turns into a check, the quantity highlight slides between options, the filter sheet slides up and can be dragged down, and cart lines slide out when removed.
- Motion is loaded lazily: components use the small `m` element, and `LazyMotion` (in `main.tsx`, `strict`) loads the engine (`lib/motionFeatures.ts`) in its own chunk. Use `m.div`, never `motion.div`.
- Home and the product list are in the main bundle; the product page, cart, checkout and order pages load as separate chunks on first visit (`app/router.tsx`).
- Everything respects `prefers-reduced-motion` (CSS, plus `MotionConfig reducedMotion="user"`).
- Prices use the `money` class (no wrap, isolated), not forced LTR, so "7 د.أ" reads correctly in Arabic. Phone numbers and order numbers are LTR.

## Dashboard behavior

The manager is not technical and works from a phone, so every screen is one column with large touch targets, and the tabs sit at the bottom in thumb reach (on wider screens they move under the header). The order is fixed: Products, Settings, Orders.

- **Private**: `noindex` (meta and `robots.txt`), never linked from the store. A `manifest.webmanifest` with a name and icons (192, 512 and the Apple touch icon) so it can be added to the home screen and opens full screen.
- **Login**: one password field. `GET /api/admin/session` decides between the login page and the tabs. Any request that answers `401 not_authenticated` (logged out elsewhere, expired, password changed on another device) clears the loaded data and shows the login page. A wrong password, `password_not_set` and the `429` wait (from `Retry-After`) each have their own sentence. Passwords are sent exactly as typed.
- **Errors**: every API error code has a sentence in both languages (`app/i18n.ts`, `errors.*`); unknown ones fall back to a generic sentence.
- **Products tab**: categories on top (tap to edit), products below with search, a category filter and a show/hide switch on each row. A visible `fixed` product without a quantity is flagged "not shown" (`shown_in_store`). Lists are paged by the API; "show more" loads the next page.
- **Product form**: one page (`/products/new`, `/products/:id`). It loads the product from `GET /api/admin/products/{id}`, always fresh when it opens: the form sends every field, so a cached copy could undo a change made since (such as hiding it from the list). Prices and quantities accept Arabic-Indic digits and `٫` or `,` as the decimal point. Existing quantity rows and colors are sent back with their `id`, so carts in the store keep working after a price change. A `quote` product does not send its quantity table, so its old rows come back if it is switched to a fixed price again. An unchanged image is left out of the save. A failed check scrolls to the first field in red.
- **Images**: picked from the phone, resized in the browser to at most 1600 px on the long side, converted to WebP under the API's `max_bytes`, and uploaded with the presigned POST before the form is saved; the form then sends only the `tmp/` key. The phone's rotation (EXIF) is applied. If the browser's `createImageBitmap` refuses the file or its options, the photo is decoded through an `<img>` instead. Safari has no WebP encoder (its canvas silently returns a PNG), so the result type is checked and a WebAssembly encoder (`@jsquash/webp`) is loaded on demand only in that case, in its own chunk.
- **Deleting** (product, category, order) takes a second tap: the button turns red and asks again, and goes back after 5 seconds. A category with products shows why it cannot be deleted instead of a delete button.
- **Settings tab**: the two delivery fees, the store WhatsApp number and the two links, checked like the API and sent only when changed (an emptied link is removed). Password change needs the current password; this device stays logged in. One logout, which logs out every device.
- **Orders tab**: the four stats, then the log, newest first: a table on wide screens, cards on phones. The search and the mark filter live in the URL, so coming back from an order keeps them. Dates are shown in Jordan time (`Asia/Amman`), like the "today" count. The log refreshes every minute.
- **Order page**: the mark (no mark, done, cancelled) saves on tap; the customer's details with a button that opens their WhatsApp chat; the items; a price per piece for each quote item, after which the server recomputes the subtotal and total; the internal note; delete.
