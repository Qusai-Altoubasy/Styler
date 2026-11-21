import { useTranslation } from "react-i18next";
import { Link } from "react-router";
import { BackIcon } from "./icons";

/** The title of a page inside a tab, with a way back to the tab. */
export function PageHead({ title, back }: { title: string; back: string }) {
  const { t } = useTranslation();
  return (
    <div className="page-head">
      <Link to={back} className="icon-btn" aria-label={t("back")}>
        <BackIcon />
      </Link>
      <h1>{title}</h1>
    </div>
  );
}
