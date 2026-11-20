import { AnimatePresence, m } from "motion/react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";
import { useTheme } from "@styler/shared/theme/theme";
import { useCartCount } from "../lib/cart";
import { BagIcon, MoonIcon, SunIcon } from "../ui/icons";
import logo from "../logo.webp";
import styles from "./Header.module.css";

export function Header() {
  const { t, i18n } = useTranslation();
  const { theme, toggle } = useTheme();
  const count = useCartCount();
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const scrollToContact = () =>
    document.getElementById("contact")?.scrollIntoView({ behavior: "smooth", block: "start" });

  return (
    <header className={styles.header} data-scrolled={scrolled}>
      <div className={`page ${styles.bar}`}>
        <Link to="/" className={styles.brand} aria-label={t("home")}>
          <img src={logo} alt="" width={40} height={40} />
          <span className={styles.wordmark}>
            <span>Styler</span>
            <small>Printing Press</small>
          </span>
        </Link>

        <nav className={styles.actions}>
          <button
            type="button"
            className={`btn btn-sm ${styles.contact}`}
            onClick={scrollToContact}
          >
            {t("contact")}
          </button>
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
            <AnimatePresence mode="wait" initial={false}>
              <m.span
                key={theme}
                className={styles.themeIcon}
                initial={{ rotate: -90, scale: 0.4, opacity: 0 }}
                animate={{ rotate: 0, scale: 1, opacity: 1 }}
                exit={{ rotate: 90, scale: 0.4, opacity: 0 }}
                transition={{ duration: 0.25 }}
              >
                {theme === "dark" ? <SunIcon /> : <MoonIcon />}
              </m.span>
            </AnimatePresence>
          </button>
          <Link
            to="/cart"
            className={`icon-btn ${styles.cart}`}
            aria-label={count ? t("cartWithCount", { count }) : t("cart")}
          >
            <BagIcon />
            {/* One badge that appears and leaves; only the number inside is keyed, so a
                new count pops in place instead of a second badge crossing the first. */}
            <AnimatePresence>
              {count > 0 && (
                <m.span
                  className={`${styles.badge} ltr`}
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  exit={{ scale: 0, opacity: 0 }}
                  transition={{ type: "spring", stiffness: 520, damping: 18 }}
                >
                  <m.span
                    key={count}
                    className={styles.badgeCount}
                    initial={{ scale: 1.7 }}
                    animate={{ scale: 1 }}
                    transition={{ type: "spring", stiffness: 520, damping: 14 }}
                  >
                    {count > 99 ? "99+" : count}
                  </m.span>
                </m.span>
              )}
            </AnimatePresence>
          </Link>
        </nav>
      </div>
    </header>
  );
}
