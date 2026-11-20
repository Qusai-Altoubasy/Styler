import { useTranslation } from "react-i18next";
import { pickOptional } from "@styler/shared/i18n/setup";
import { useLang } from "@styler/shared/i18n/useLang";
import styles from "./LineDetails.module.css";

/** Only what is shown: a cart line's tier or a saved order item both fit. */
export interface LineQuantity {
  quantity: number;
  note_ar: string | null;
  note_en: string | null;
}
export interface LineColor {
  name_ar: string | null;
  name_en: string | null;
  hex: string;
}

/** The chosen quantity (or approximate quantity) and color of a cart line or order item. */
export function LineDetails({
  tier,
  color,
  approxQuantity,
}: {
  tier: LineQuantity | null;
  color: LineColor | null;
  approxQuantity: number | null;
}) {
  const { t } = useTranslation();
  const lang = useLang();
  const note = tier ? pickOptional(tier, "note", lang) : null;

  return (
    <p className={styles.details}>
      {tier && (
        <span>
          {t("pieces", { count: tier.quantity })}
          {note && ` (${note})`}
        </span>
      )}
      {approxQuantity !== null && <span>{t("approxQty", { count: approxQuantity })}</span>}
      {color && (
        <span className={styles.color}>
          <i style={{ background: color.hex }} aria-hidden="true" />
          {pickOptional(color, "name", lang)}
        </span>
      )}
    </p>
  );
}
