# frontend

The real customer storefront and manager dashboard. Not started yet (phase 3). The prototype in ../mvp is a suggested look, not a binding spec.

Stack: Vite, React, TypeScript, React Router, TanStack Query, an i18n library for Arabic (RTL) and English (LTR), pnpm workspaces.

## Structure

Two separate apps with no link between them, plus shared code. Inside each app the code is feature-based.

```
frontend/
├── package.json                     # pnpm workspaces
├── shared/                          # @styler/shared
│   ├── api/                         # API types generated from the FastAPI OpenAPI (openapi-typescript)
│   ├── i18n/                        # Arabic/English setup, RTL/LTR
│   ├── theme/                       # brand colors, light and dark mode
│   ├── ui/                          # small shared components
│   └── utils/                       # money formatting, phone validation
├── storefront/src/                  # main domain, talks to /api/*
│   ├── app/                         # router, providers, header, footer
│   └── features/
│       ├── catalog/                 # home, product list, filters
│       ├── product/                 # product page
│       ├── cart/                    # cart (localStorage)
│       └── checkout/                # form, WhatsApp message, "we got your order"
└── admin/src/                       # admin.<domain>, talks to /api/admin/*
    ├── app/                         # router, login guard, tabs
    └── features/
        ├── auth/
        ├── catalog/                 # categories on top, products below
        ├── settings/
        ├── orders/
        └── media/                   # resize in the browser, then upload
```

## Rules

- Each feature holds its components, its `api.ts` (TanStack Query hooks) and its own translation strings.
- A feature never imports from inside another feature. Anything needed by more than one feature moves to `shared/`.
- API types are generated, never written by hand, so a backend change breaks the build until the frontend is fixed.
- Totals in the cart are for display only. The server recalculates every order and is the source of truth.
