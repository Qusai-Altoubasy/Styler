import { createBrowserRouter, Navigate } from "react-router";
import { CategoryFormPage } from "../features/catalog/CategoryFormPage";
import { ProductFormPage } from "../features/catalog/ProductFormPage";
import { ProductsTab } from "../features/catalog/ProductsTab";
import { OrderPage } from "../features/orders/OrderPage";
import { OrdersTab } from "../features/orders/OrdersTab";
import { SettingsTab } from "../features/settings/SettingsTab";
import { Layout } from "./Layout";
import { NotFound } from "./StatusPages";

// One small app for one person: every page is in the main bundle, so switching tabs on a
// phone never waits for a chunk.
export const router = createBrowserRouter([
  {
    element: <Layout />,
    children: [
      { path: "/", element: <Navigate to="/products" replace /> },
      { path: "/products", element: <ProductsTab /> },
      { path: "/products/new", element: <ProductFormPage /> },
      { path: "/products/:productId", element: <ProductFormPage /> },
      // Under /products, so the Products tab stays highlighted while editing a category.
      { path: "/products/categories/new", element: <CategoryFormPage /> },
      { path: "/products/categories/:categoryId", element: <CategoryFormPage /> },
      { path: "/settings", element: <SettingsTab /> },
      { path: "/orders", element: <OrdersTab /> },
      { path: "/orders/:orderId", element: <OrderPage /> },
      { path: "*", element: <NotFound /> },
    ],
  },
]);
