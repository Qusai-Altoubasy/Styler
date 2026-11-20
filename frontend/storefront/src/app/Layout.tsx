import { Outlet, ScrollRestoration, useLocation } from "react-router";
import { Footer } from "./Footer";
import { Header } from "./Header";

export function Layout() {
  const { pathname } = useLocation();
  return (
    <>
      <Header />
      <main key={pathname} className="route-enter">
        <Outlet />
      </main>
      <Footer />
      <ScrollRestoration />
    </>
  );
}
