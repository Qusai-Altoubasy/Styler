import { useTranslation } from "react-i18next";
import { Link } from "react-router";
import styles from "./StatusPages.module.css";

export function NotFound() {
  const { t } = useTranslation();
  return (
    <div className={`page ${styles.status}`}>
      <p className={styles.code}>404</p>
      <p>{t("notFound")}</p>
      <Link to="/" className="btn btn-primary">
        {t("backHome")}
      </Link>
    </div>
  );
}

export function LoadError({ onRetry }: { onRetry: () => void }) {
  const { t } = useTranslation();
  return (
    <div className={`page ${styles.status}`} role="alert">
      <p>{t("loadError")}</p>
      <button type="button" className="btn" onClick={onRetry}>
        {t("retry")}
      </button>
    </div>
  );
}
