# frontend

The customer storefront and the manager dashboard. The storefront is built (phase 3); the dashboard in `admin/` comes in phase 4. The prototype in ../mvp is a suggested look, not a binding spec.

Stack: Vite, React 19, TypeScript (strict), React Router, TanStack Query, i18next for Arabic (RTL) and English (LTR), Motion for animations, pnpm workspaces, eslint, prettier, vitest.

## Local development

pnpm runs through corepack (bundled with Node), pinned by `packageManager` in `package.json`, so nothing is installed globally.

```bash
cd frontend
corepack pnpm install
cp storefront/.env.example storefront/.env   # then fill in the two proxy targets
corepack pnpm --dir storefront dev           # http://localhost:5173
```

The backend must be running (`deploy/compose.dev.yaml`). The dev server proxies `/api/*` to the api container and `/media/*` to MinIO, so the app talks to the API on its own origin, as it will behind CloudFront. Both targets come from `storefront/.env` with no defaults: a missing value stops the dev server.

| Command (from `frontend/`)             | What it does                                                                  |
| -------------------------------------- | ----------------------------------------------------------------------------- |
| `corepack pnpm gen:api`                | Regenerates `shared/api/schema.d.ts` from the running api container's OpenAPI |
| `corepack pnpm typecheck`              | `tsc` over every package                                                      |
| `corepack pnpm lint`                   | eslint (typescript-eslint strict, React hooks rules)                          |
| `corepack pnpm format`                 | prettier                                                                      |
| `corepack pnpm test`                   | vitest: pricing, cart checks, filters, phone, money and the WhatsApp message  |
| `corepack pnpm --dir storefront build` | Production build into `storefront/dist`                                       |

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
└── admin/src/                       # phase 4: admin.<domain>, talks to /api/admin/*
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
- The home heading prints like a press run: cyan, magenta and yellow layers land out of register, slide into place, then the black layer prints. It plays once per visit.
- Images sit in frames with crop marks. Products without an image show a halftone pattern in their category's ink.
- Cards slide off register on hover or tap, showing the category color underneath.
- Other motion answers the customer's actions: the cart badge pops, add-to-cart turns into a check, the quantity highlight slides between options, the filter sheet slides up and can be dragged down, and cart lines slide out when removed.
- Motion is loaded lazily: components use the small `m` element, and `LazyMotion` (in `main.tsx`, `strict`) loads the engine (`lib/motionFeatures.ts`) in its own chunk. Use `m.div`, never `motion.div`.
- Home and the product list are in the main bundle; the product page, cart, checkout and order pages load as separate chunks on first visit (`app/router.tsx`).
- Everything respects `prefers-reduced-motion` (CSS, plus `MotionConfig reducedMotion="user"`).
- Prices use the `money` class (no wrap, isolated), not forced LTR, so "7 د.أ" reads correctly in Arabic. Phone numbers and order numbers are LTR.
