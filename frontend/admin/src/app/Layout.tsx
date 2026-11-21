import { useTranslation } from "react-i18next";
import { NavLink, Outlet, ScrollRestoration } from "react-router";
import { useTheme } from "@styler/shared/theme/theme";
import { LoginPage } from "../features/auth/LoginPage";
import { useSession } from "../lib/session";
import { BoxIcon, GearIcon, MoonIcon, ReceiptIcon, SunIcon } from "../ui/icons";
import logo from "../logo.webp";
import { LoadError, Loading } from "./StatusPages";
import styles from "./Layout.module.css";

/** Tab order is fixed by the decisions: Products, Settings, Orders. */
const TABS = [
  { to: "/products", label: "tabProducts", Icon: BoxIcon },
  { to: "/settings", label: "tabSettings", Icon: GearIcon },
  { to: "/orders", label: "tabOrders", Icon: ReceiptIcon },
] as const;

export function Layout() {
  const { t } = useTranslation();
  const session = useSession();

  return (
    <div className={styles.shell}>
      <Header />
      {session.isPending ? (
        <Loading />
      ) : session.isError ? (
        <LoadError onRetry={() => void session.refetch()} />
      ) : session.data === null ? (
        <LoginPage />
      ) : (
        <>
          <nav className={styles.tabs} aria-label={t("tabs")}>
            {TABS.map(({ to, label, Icon }) => (
              <NavLink key={to} to={to} className={styles.tab}>
                <Icon />
                <span>{t(label)}</span>
              </NavLink>
            ))}
          </nav>
          <main className={`page ${styles.main}`}>
            <Outlet />
          </main>
          {/* A new page opens at the top; "back" returns to where the list was. */}
          <ScrollRestoration />
        </>
      )}
    </div>
  );
}

function Header() {
  const { t, i18n } = useTranslation();
  const { theme, toggle } = useTheme();
  return (
    <header className={styles.header}>
      <div className={`page ${styles.bar}`}>
        <div className={styles.brand}>
          <img src={logo} alt="" width={36} height={36} />
          <span className={styles.wordmark}>
            <span>Styler</span>
            <small>{t("dashboard")}</small>
          </span>
        </div>
        <div className={styles.actions}>
          <button
            type="button"
            className={`icon-btn ${styles.lang}`}
            onClick={() => void i18n.changeLanguage(i18n.language === "en" ? "ar" : "en")}
            aria-label={t("switchLangLabel")}
            lang={i18n.language === "en" ? "ar" : "en"}
          >
            {i18n.language === "en" ? "ع" : "EN"}
          </button>
          <button
            type="button"
            className="icon-btn"
            onClick={toggle}
            aria-label={theme === "dark" ? t("themeLight") : t("themeDark")}
          >
            {theme === "dark" ? <SunIcon /> : <MoonIcon />}
          </button>
        </div>
      </div>
    </header>
  );
}
