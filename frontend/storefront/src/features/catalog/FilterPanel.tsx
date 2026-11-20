import { m } from "motion/react";
import { useEffect, useEffectEvent, useId, useState } from "react";
import { useTranslation } from "react-i18next";
import type { CategoryCard, PricingMode } from "@styler/shared/api/types";
import { pick } from "@styler/shared/i18n/setup";
import { useLang } from "@styler/shared/i18n/useLang";
import { toAsciiDecimal } from "@styler/shared/utils/digits";
import type { ProductFilters } from "./api";
import { isPrice } from "./filterParams";
import styles from "./FilterPanel.module.css";

interface Props {
  filters: ProductFilters;
  categories: CategoryCard[];
  onChange: (patch: Partial<ProductFilters>) => void;
}

export function FilterPanel({ filters, categories, onChange }: Props) {
  const { t } = useTranslation("catalog");
  const lang = useLang();
  const id = useId();

  const modes: { value: PricingMode | null; label: string }[] = [
    { value: null, label: t("pricingAny") },
    { value: "fixed", label: t("pricingFixed") },
    { value: "quote", label: t("pricingQuote") },
  ];

  return (
    <div className={styles.panel}>
      <fieldset className={styles.group}>
        <legend>{t("category")}</legend>
        <div className={styles.pills}>
          <Pill active={filters.categoryId === null} onClick={() => onChange({ categoryId: null })}>
            {t("allCategories")}
          </Pill>
          {categories.map((c) => (
            <Pill
              key={c.id}
              active={filters.categoryId === c.id}
              ink={c.color === "black" ? "key" : c.color}
              onClick={() => onChange({ categoryId: c.id })}
            >
              {pick(c, "name", lang)}
            </Pill>
          ))}
        </div>
      </fieldset>

      <fieldset className={styles.group}>
        <legend>{t("price")}</legend>
        <PriceRange
          min={filters.minPrice}
          max={filters.maxPrice}
          onCommit={(minPrice, maxPrice) => onChange({ minPrice, maxPrice })}
        />
        <p className={styles.hint}>{t("priceHint")}</p>
      </fieldset>

      <fieldset className={styles.group}>
        <legend>{t("pricing")}</legend>
        <div className={styles.segmented} role="radiogroup">
          {modes.map((option) => {
            const active = filters.mode === option.value;
            return (
              <button
                key={option.label}
                type="button"
                role="radio"
                aria-checked={active}
                className={styles.segment}
                onClick={() => onChange({ mode: option.value })}
              >
                {active && (
                  <m.span
                    layoutId={`${id}-mode`}
                    className={styles.segmentThumb}
                    transition={{ type: "spring", stiffness: 500, damping: 36 }}
                  />
                )}
                <span className={styles.segmentLabel}>{option.label}</span>
              </button>
            );
          })}
        </div>
      </fieldset>

      <label className={styles.switchRow}>
        <span>{t("freeDeliveryOnly")}</span>
        <input
          type="checkbox"
          role="switch"
          className={styles.switch}
          checked={filters.freeDelivery}
          onChange={(e) => onChange({ freeDelivery: e.target.checked })}
        />
      </label>
    </div>
  );
}

function Pill({
  active,
  ink,
  onClick,
  children,
}: {
  active: boolean;
  ink?: string;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      className={styles.pill}
      aria-pressed={active}
      onClick={onClick}
      style={ink ? ({ "--pill": `var(--${ink})` } as React.CSSProperties) : undefined}
    >
      {children}
    </button>
  );
}

/** Two price inputs that apply once typing pauses and both values are valid. */
function PriceRange({
  min,
  max,
  onCommit,
}: {
  min: string;
  max: string;
  onCommit: (min: string, max: string) => void;
}) {
  const { t } = useTranslation("catalog");
  const [draft, setDraft] = useState({ min, max });

  // Follow outside changes (a chip removed, "clear all") without an effect.
  const [shown, setShown] = useState({ min, max });
  if (shown.min !== min || shown.max !== max) {
    setShown({ min, max });
    setDraft({ min, max });
  }

  // Stable, so a re-render of the page does not restart the pause timer.
  const commit = useEffectEvent((a: string, b: string) => onCommit(a, b));
  useEffect(() => {
    if (draft.min === min && draft.max === max) return;
    if (!isPrice(draft.min) || !isPrice(draft.max)) return;
    const timer = setTimeout(() => commit(draft.min, draft.max), 500);
    return () => clearTimeout(timer);
  }, [draft, min, max]);

  const input = (key: "min" | "max", label: string) => (
    <label className={styles.priceField}>
      <span>{label}</span>
      <input
        className="input"
        inputMode="decimal"
        dir="ltr"
        value={draft[key]}
        aria-invalid={!isPrice(draft[key])}
        onChange={(e) =>
          setDraft((d) => ({ ...d, [key]: toAsciiDecimal(e.target.value).replace(/[^\d.]/g, "") }))
        }
      />
    </label>
  );

  return (
    <div className={styles.priceRow}>
      {input("min", t("priceFrom"))}
      {input("max", t("priceTo"))}
    </div>
  );
}
