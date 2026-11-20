import { AnimatePresence, m } from "motion/react";
import { useCallback, useEffect, useEffectEvent, useState } from "react";
import { useCategories, useCategoryInk } from "../../lib/categories";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router";
import type { ProductSort } from "@styler/shared/api/types";
import { pick } from "@styler/shared/i18n/setup";
import { useLang } from "@styler/shared/i18n/useLang";
import { LoadError } from "../../app/StatusPages";
import { BottomSheet } from "../../ui/BottomSheet";
import { CloseIcon, SearchIcon, SlidersIcon } from "../../ui/icons";
import { type ProductFilters, useProducts } from "./api";
import { activeFilterCount, readFilters, writeFilters } from "./filterParams";
import { FilterPanel } from "./FilterPanel";
import { ProductCard } from "./ProductCard";
import styles from "./ProductsPage.module.css";

export function ProductsPage() {
  const { t } = useTranslation("catalog");
  const lang = useLang();
  const [params, setParams] = useSearchParams();
  const filters = readFilters(params);
  const categories = useCategories();
  const inkOf = useCategoryInk();
  const products = useProducts(filters, lang);
  const [sheetOpen, setSheetOpen] = useState(false);

  const update = useCallback(
    (patch: Partial<ProductFilters>) =>
      setParams((current) => writeFilters({ ...readFilters(current), ...patch }), {
        replace: true,
        preventScrollReset: true,
      }),
    [setParams],
  );

  const category = categories.data?.find((c) => c.id === filters.categoryId);
  const activeCount = activeFilterCount(filters);
  const closeSheet = useCallback(() => setSheetOpen(false), []);

  const chips: { key: string; label: string; clear: Partial<ProductFilters> }[] = [];
  if (category)
    chips.push({ key: "c", label: pick(category, "name", lang), clear: { categoryId: null } });
  if (filters.minPrice || filters.maxPrice)
    chips.push({
      key: "p",
      label: t("priceChip", { range: `${filters.minPrice || "0"}–${filters.maxPrice || "∞"}` }),
      clear: { minPrice: "", maxPrice: "" },
    });
  if (filters.mode)
    chips.push({
      key: "m",
      label: filters.mode === "fixed" ? t("pricingFixed") : t("pricingQuote"),
      clear: { mode: null },
    });
  if (filters.freeDelivery)
    chips.push({ key: "f", label: t("freeDeliveryOnly"), clear: { freeDelivery: false } });

  const panel = (
    <FilterPanel filters={filters} categories={categories.data ?? []} onChange={update} />
  );
  const count = products.data?.length ?? 0;

  return (
    <div className={`page ${styles.layout}`}>
      <aside className={styles.sidebar} aria-label={t("filters")}>
        {panel}
      </aside>

      <section className={styles.main}>
        <header className={styles.head}>
          <h1>{category ? pick(category, "name", lang) : t("productsTitle")}</h1>
          <p className="muted" aria-live="polite">
            {products.data ? t("resultCount", { count }) : " "}
          </p>
        </header>

        <div className={styles.toolbar}>
          <SearchBox value={filters.q} onCommit={(q) => update({ q })} />
          <label className={styles.sort}>
            <span className="visually-hidden">{t("sort")}</span>
            <select
              className="input"
              value={filters.sort}
              onChange={(e) => update({ sort: e.target.value as ProductSort })}
            >
              <option value="default">{t("sortDefault")}</option>
              <option value="price_asc">{t("sortPriceAsc")}</option>
              <option value="price_desc">{t("sortPriceDesc")}</option>
              <option value="name">{t("sortName")}</option>
            </select>
          </label>
          <button
            type="button"
            className={`btn ${styles.filterBtn}`}
            onClick={() => setSheetOpen(true)}
            data-active={activeCount > 0}
          >
            <SlidersIcon size={18} />
            {activeCount ? t("filtersWithCount", { count: activeCount }) : t("filters")}
          </button>
        </div>

        <AnimatePresence initial={false}>
          {chips.length > 0 && (
            <m.ul
              className={styles.chips}
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
            >
              <AnimatePresence initial={false} mode="popLayout">
                {chips.map((chip) => (
                  <m.li
                    key={chip.key}
                    layout
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.8 }}
                  >
                    <button
                      type="button"
                      className={styles.chip}
                      onClick={() => update(chip.clear)}
                      aria-label={t("removeFilter", { label: chip.label })}
                    >
                      {chip.label}
                      <CloseIcon size={14} />
                    </button>
                  </m.li>
                ))}
                {chips.length > 1 && (
                  <m.li key="clear" layout>
                    <button
                      type="button"
                      className={styles.clearAll}
                      onClick={() =>
                        update({
                          categoryId: null,
                          minPrice: "",
                          maxPrice: "",
                          mode: null,
                          freeDelivery: false,
                        })
                      }
                    >
                      {t("clearAll")}
                    </button>
                  </m.li>
                )}
              </AnimatePresence>
            </m.ul>
          )}
        </AnimatePresence>

        {products.isError ? (
          <LoadError onRetry={() => void products.refetch()} />
        ) : products.isPending ? (
          <ul className={styles.grid}>
            {Array.from({ length: 8 }, (_, i) => (
              <li key={i} className={`skeleton ${styles.skeleton}`} />
            ))}
          </ul>
        ) : count === 0 ? (
          <div className={styles.empty}>
            <p>{t("noResults")}</p>
            {activeCount + Number(Boolean(filters.q)) > 0 && (
              <button
                type="button"
                className="btn"
                onClick={() => setParams(new URLSearchParams(), { replace: true })}
              >
                {t("clearAll")}
              </button>
            )}
          </div>
        ) : (
          <m.ul className={styles.grid} data-loading={products.isPlaceholderData}>
            <AnimatePresence initial={false} mode="popLayout">
              {products.data.map((product) => (
                <ProductCard key={product.id} product={product} ink={inkOf(product.category_id)} />
              ))}
            </AnimatePresence>
          </m.ul>
        )}
      </section>

      <BottomSheet
        open={sheetOpen}
        onClose={closeSheet}
        title={t("filters")}
        closeLabel={t("close")}
        footer={
          <button type="button" className="btn btn-primary btn-block" onClick={closeSheet}>
            {t("showResults", { count })}
          </button>
        }
      >
        {panel}
      </BottomSheet>
    </div>
  );
}

/** Applies the search once typing pauses, without a submit button. */
function SearchBox({ value, onCommit }: { value: string; onCommit: (q: string) => void }) {
  const { t } = useTranslation("catalog");
  const [draft, setDraft] = useState(value);
  // Follow outside changes (a cleared filter, the back button) without an effect.
  const [shown, setShown] = useState(value);
  if (shown !== value) {
    setShown(value);
    setDraft(value);
  }
  // A stable callback: re-renders of the page (new URL, query results) must not
  // restart the pause timer.
  const commit = useEffectEvent((q: string) => onCommit(q));
  useEffect(() => {
    // Compared trimmed, as the URL stores it: a box holding only spaces is already
    // "no search", so nothing is committed and the URL is left alone.
    if (draft.trim() === value.trim()) return;
    const timer = setTimeout(() => commit(draft), 300);
    return () => clearTimeout(timer);
  }, [draft, value]);

  return (
    <label className={styles.search}>
      <SearchIcon size={18} />
      <span className="visually-hidden">{t("search")}</span>
      <input
        className="input"
        type="search"
        enterKeyHint="search"
        placeholder={t("searchPlaceholder")}
        value={draft}
        maxLength={100}
        onChange={(e) => setDraft(e.target.value)}
      />
    </label>
  );
}
