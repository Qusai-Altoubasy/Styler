import { useTranslation } from "react-i18next";

/** "12 of 80" and a button for the next page, under a paged list. Hidden when all are shown. */
export function LoadMore({
  shown,
  total,
  loading,
  onMore,
}: {
  shown: number;
  total: number;
  loading: boolean;
  onMore: () => void;
}) {
  const { t } = useTranslation();
  if (shown >= total) return null;
  return (
    <div className="load-more">
      <small className="muted">{t("shownOf", { shown, total })}</small>
      <button type="button" className="btn btn-sm" disabled={loading} onClick={onMore}>
        {t("loadMore")}
      </button>
    </div>
  );
}
