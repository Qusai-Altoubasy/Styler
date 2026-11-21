import { useTranslation } from "react-i18next";
import { PlusIcon, TrashIcon } from "../../ui/icons";
import { emptyTier, type TierRow } from "./productForm";
import { TextField } from "../../ui/TextField";
import styles from "./forms.module.css";

/** The quantity table of a fixed-price product: quantity, price and an optional note. */
export function TiersEditor({
  tiers,
  onChange,
  fieldError,
}: {
  tiers: TierRow[];
  onChange: (next: TierRow[]) => void;
  fieldError: (key: string) => string | null;
}) {
  const { t } = useTranslation("catalog");
  const edit = (uid: string, patch: Partial<TierRow>) =>
    onChange(tiers.map((tier) => (tier.uid === uid ? { ...tier, ...patch } : tier)));

  return (
    <>
      <ol className={styles.rows}>
        {tiers.map((tier, index) => (
          <li key={tier.uid} className={styles.row}>
            <div className={styles.rowHead}>
              <span>{t("tierNumber", { n: index + 1 })}</span>
              <button
                type="button"
                className="icon-btn"
                aria-label={t("removeTier")}
                onClick={() => onChange(tiers.filter((row) => row.uid !== tier.uid))}
              >
                <TrashIcon size={18} />
              </button>
            </div>
            <div className={styles.pair}>
              <TextField
                label={t("quantity")}
                value={tier.quantity}
                onChange={(quantity) => edit(tier.uid, { quantity })}
                inputMode="numeric"
                dir="ltr"
                placeholder="250"
                error={fieldError(`tier.${tier.uid}.quantity`)}
              />
              <TextField
                label={t("price")}
                value={tier.price}
                onChange={(price) => edit(tier.uid, { price })}
                inputMode="decimal"
                dir="ltr"
                placeholder="7"
                error={fieldError(`tier.${tier.uid}.price`)}
              />
            </div>
            <div className={styles.pair}>
              <TextField
                label={t("noteAr")}
                optional={t("common:optional")}
                value={tier.noteAr}
                onChange={(noteAr) => edit(tier.uid, { noteAr })}
                dir="rtl"
                maxLength={200}
                placeholder={t("notePlaceholderAr")}
              />
              <TextField
                label={t("noteEn")}
                optional={t("common:optional")}
                value={tier.noteEn}
                onChange={(noteEn) => edit(tier.uid, { noteEn })}
                dir="ltr"
                maxLength={200}
                placeholder={t("notePlaceholderEn")}
              />
            </div>
          </li>
        ))}
      </ol>
      {tiers.length < 50 && (
        <button type="button" className="btn" onClick={() => onChange([...tiers, emptyTier()])}>
          <PlusIcon size={18} />
          {t("addTier")}
        </button>
      )}
    </>
  );
}
