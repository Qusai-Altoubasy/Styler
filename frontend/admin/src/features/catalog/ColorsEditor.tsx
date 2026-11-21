import { useTranslation } from "react-i18next";
import { PlusIcon, TrashIcon } from "../../ui/icons";
import { Switch } from "../../ui/Switch";
import { emptyColor, type ColorRow } from "./productForm";
import { TextField } from "../../ui/TextField";
import styles from "./forms.module.css";

/** Quick picks; any shade can still be chosen with the color picker. */
const PRESETS = [
  "#ffffff",
  "#16171b",
  "#9ca3af",
  "#d62828",
  "#f77f00",
  "#f5c400",
  "#2a9d4b",
  "#0093cf",
  "#1d3a8a",
  "#7b2cbf",
  "#d6006f",
  "#8b5a2b",
];

export function ColorsEditor({
  hasColors,
  colors,
  onChange,
  fieldError,
}: {
  hasColors: boolean;
  colors: ColorRow[];
  onChange: (patch: { hasColors?: boolean; colors?: ColorRow[] }) => void;
  fieldError: (key: string) => string | null;
}) {
  const { t } = useTranslation("catalog");
  const edit = (uid: string, patch: Partial<ColorRow>) =>
    onChange({
      colors: colors.map((color) => (color.uid === uid ? { ...color, ...patch } : color)),
    });

  return (
    <>
      <Switch
        checked={hasColors}
        onChange={(on) =>
          // Turning colors on starts with one empty row to fill in.
          onChange(
            on && colors.length === 0
              ? { hasColors: on, colors: [emptyColor()] }
              : { hasColors: on },
          )
        }
        label={t("hasColors")}
        hint={t("hasColorsHint")}
      />
      {hasColors && (
        <>
          <ol className={styles.rows}>
            {colors.map((color, index) => (
              <li key={color.uid} className={styles.row}>
                <div className={styles.rowHead}>
                  <span>{t("colorName", { n: index + 1 })}</span>
                  <button
                    type="button"
                    className="icon-btn"
                    aria-label={t("removeColor")}
                    onClick={() =>
                      onChange({ colors: colors.filter((row) => row.uid !== color.uid) })
                    }
                  >
                    <TrashIcon size={18} />
                  </button>
                </div>
                <div className={styles.colorRow}>
                  <label className={styles.hex} style={{ background: color.hex }}>
                    <input
                      type="color"
                      value={color.hex}
                      onChange={(event) => edit(color.uid, { hex: event.target.value })}
                      aria-label={t("pickColor")}
                    />
                  </label>
                  <div className={styles.presets}>
                    {PRESETS.map((hex) => (
                      <button
                        key={hex}
                        type="button"
                        className={styles.preset}
                        style={{ background: hex }}
                        aria-label={hex}
                        aria-pressed={color.hex === hex}
                        onClick={() => edit(color.uid, { hex })}
                      />
                    ))}
                  </div>
                </div>
                <div className={styles.pair}>
                  <TextField
                    label={t("common:nameAr")}
                    value={color.nameAr}
                    onChange={(nameAr) => edit(color.uid, { nameAr })}
                    dir="rtl"
                    maxLength={50}
                    error={fieldError(`color.${color.uid}.nameAr`)}
                  />
                  <TextField
                    label={t("common:nameEn")}
                    value={color.nameEn}
                    onChange={(nameEn) => edit(color.uid, { nameEn })}
                    dir="ltr"
                    maxLength={50}
                    error={fieldError(`color.${color.uid}.nameEn`)}
                  />
                </div>
              </li>
            ))}
          </ol>
          {colors.length === 0 && <p className={styles.warn}>{t("noColorsWarning")}</p>}
          {colors.length < 30 && (
            <button
              type="button"
              className="btn"
              onClick={() => onChange({ colors: [...colors, emptyColor()] })}
            >
              <PlusIcon size={18} />
              {t("addColor")}
            </button>
          )}
        </>
      )}
    </>
  );
}
