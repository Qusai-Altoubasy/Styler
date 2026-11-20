import { createBrowserRouter } from "react-router";
import { HomePage } from "../features/catalog/HomePage";
import { ProductsPage } from "../features/catalog/ProductsPage";
import { Layout } from "./Layout";
import { NotFound } from "./StatusPages";

// Home and the product list load with the app: most visits start there. The other
// pages are split into their own chunks and load when first opened.
export const router = createBrowserRouter([
  {
    element: <Layout />,
    HydrateFallback: () => null,
    children: [
      { path: "/", element: <HomePage /> },
      { path: "/products", element: <ProductsPage /> },
      {
        path: "/products/:productId",
        lazy: async () => ({
          Component: (await import("../features/product/ProductPage")).ProductPage,
        }),
      },
      {
        path: "/cart",
        lazy: async () => ({ Component: (await import("../features/cart/CartPage")).CartPage }),
      },
      {
        path: "/checkout",
        lazy: async () => ({
          Component: (await import("../features/checkout/CheckoutPage")).CheckoutPage,
        }),
      },
      {
        path: "/order/:orderId",
        lazy: async () => ({
          Component: (await import("../features/checkout/OrderReceivedPage")).OrderReceivedPage,
        }),
      },
      { path: "*", element: <NotFound /> },
    ],
  },
]);
