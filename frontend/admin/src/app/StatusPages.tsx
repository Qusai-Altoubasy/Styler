import { useTranslation } from "react-i18next";
import { Link } from "react-router";

export function NotFound() {
  const { t } = useTranslation();
  return (
    <div className="status-box">
      <p>{t("notFound")}</p>
      <Link to="/products" className="btn">
        {t("tabProducts")}
      </Link>
    </div>
  );
}

/** A failed load, with a button that tries again. */
export function LoadError({ onRetry, message }: { onRetry: () => void; message?: string }) {
  const { t } = useTranslation();
  return (
    <div className="status-box" role="alert">
      <p>{message ?? t("loadError")}</p>
      <button type="button" className="btn" onClick={onRetry}>
        {t("retry")}
      </button>
    </div>
  );
}

export function Loading() {
  const { t } = useTranslation();
  return (
    <div className="status-box" aria-busy="true">
      <span className="spinner" aria-hidden="true" />
      <span className="visually-hidden">{t("loading")}</span>
    </div>
  );
}
