import { useState, type CSSProperties } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";
import type { AdminCategory, AdminProduct } from "@styler/shared/api/types";
import { pick } from "@styler/shared/i18n/setup";
import { useLang } from "@styler/shared/i18n/useLang";
import { formatMoney } from "@styler/shared/utils/money";
import { LoadError, Loading } from "../../app/StatusPages";
import { useErrorText } from "../../lib/errors";
import { useDebounced } from "../../lib/useDebounced";
import { inkVar } from "@styler/shared/theme/ink";
import { ChevronIcon, ImageIcon, PlusIcon } from "../../ui/icons";
import { LoadMore } from "../../ui/LoadMore";
import { SearchBox } from "../../ui/SearchBox";
import { useCategories, useProducts, useUpdateProduct } from "./api";
import styles from "./ProductsTab.module.css";

/** Categories on top, products below (the decided layout of the Products tab). */
export function ProductsTab() {
  const categories = useCategories();
  if (categories.isPending) return <Loading />;
  if (categories.isError) return <LoadError onRetry={() => void categories.refetch()} />;
  return (
    <>
      <CategoriesSection categories={categories.data} />
      <ProductsSection categories={categories.data} />
    </>
  );
}

function CategoriesSection({ categories }: { categories: AdminCategory[] }) {
  const { t } = useTranslation("catalog");
  const lang = useLang();
  return (
    <section className="card">
      <h2 className="card-title">
        {t("categories")}
        <Link to="/products/categories/new" className="btn btn-sm">
          <PlusIcon size={18} />
          {t("addCategory")}
        </Link>
      </h2>
      {categories.length === 0 ? (
        <p className="empty">{t("noCategories")}</p>
      ) : (
        <>
          <p className="card-hint">{t("categoriesHint")}</p>
          <ul className={styles.categories}>
            {categories.map((category) => (
              <li key={category.id}>
                <Link
                  to={`/products/categories/${category.id}`}
                  className={styles.category}
                  style={{ "--ink-color": inkVar(category.color) } as CSSProperties}
                >
                  <span className={styles.categoryImage}>
                    {category.image_url && <img src={category.image_url} alt="" loading="lazy" />}
                  </span>
                  <span className={styles.categoryText}>
                    <strong>{pick(category, "name", lang)}</strong>
                    <small className="muted">
                      {t("productCount", { count: category.product_count })}
                    </small>
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}

function ProductsSection({ categories }: { categories: AdminCategory[] }) {
  const { t } = useTranslation("catalog");
  const [q, setQ] = useState("");
  const [categoryId, setCategoryId] = useState<number | null>(null);
  // The list follows the search box without a request on every key press.
  const debouncedQ = useDebounced(q);
  const products = useProducts({ q: debouncedQ, categoryId });
  const names = new Map(categories.map((category) => [category.id, category]));
  const items = products.data?.pages.flatMap((page) => page.items) ?? [];
  const total = products.data?.pages[0]?.total ?? 0;
  const filtered = q.trim() !== "" || categoryId !== null;

  return (
    <section className="card">
      <h2 className="card-title">
        {t("products")}
        {categories.length > 0 && (
          <Link to="/products/new" className="btn btn-sm btn-primary">
            <PlusIcon size={18} />
            {t("addProduct")}
          </Link>
        )}
      </h2>
      {categories.length === 0 ? (
        <p className="empty">{t("needCategoryFirst")}</p>
      ) : (
        <>
          <div className={styles.filters}>
            <SearchBox value={q} onChange={setQ} placeholder={t("search")} />
            <select
              className="input"
              value={categoryId ?? ""}
              onChange={(event) =>
                setCategoryId(event.target.value ? Number(event.target.value) : null)
              }
              aria-label={t("category")}
            >
              <option value="">{t("allCategories")}</option>
              {categories.map((category) => (
                <CategoryOption key={category.id} category={category} />
              ))}
            </select>
          </div>

          {products.isPending ? (
            <Loading />
          ) : products.isError ? (
            <LoadError onRetry={() => void products.refetch()} />
          ) : items.length === 0 ? (
            <p className="empty">{filtered ? t("noMatch") : t("noProducts")}</p>
          ) : (
            <>
              <ul className={styles.products} aria-busy={products.isPlaceholderData}>
                {items.map((product) => (
                  <ProductRow
                    key={product.id}
                    product={product}
                    category={names.get(product.category_id)}
                  />
                ))}
              </ul>
              <LoadMore
                shown={items.length}
                total={total}
                loading={products.isFetchingNextPage}
                onMore={() => void products.fetchNextPage()}
              />
            </>
          )}
        </>
      )}
    </section>
  );
}

export function CategoryOption({ category }: { category: AdminCategory }) {
  const lang = useLang();
  return <option value={category.id}>{pick(category, "name", lang)}</option>;
}

function ProductRow({ product, category }: { product: AdminProduct; category?: AdminCategory }) {
  const { t } = useTranslation("catalog");
  const lang = useLang();
  const update = useUpdateProduct();
  const errorText = useErrorText();
  // Shown right away while the save runs; the list refreshes after it.
  const visible = update.isPending
    ? (update.variables.body.is_visible ?? product.is_visible)
    : product.is_visible;

  return (
    <li className={styles.product} data-hidden={!visible}>
      <Link to={`/products/${product.id}`} className={styles.productLink}>
        <span className="thumb">
          {product.image_url ? (
            <img src={product.image_url} alt="" loading="lazy" />
          ) : (
            <ImageIcon size={22} />
          )}
        </span>
        <span className={styles.productText}>
          <strong>{pick(product, "name", lang)}</strong>
          <small className="muted">
            {category ? pick(category, "name", lang) : ""}
            {" · "}
            {product.pricing_mode === "quote" ? (
              t("common:quote")
            ) : product.price ? (
              <span className="money">
                {t("from", { price: formatMoney(product.price, lang) })}
              </span>
            ) : (
              "—"
            )}
          </small>
          <span className={styles.tags}>
            {!product.is_visible && <span className="tag tag-hidden">{t("hidden")}</span>}
            {product.is_visible && !product.shown_in_store && (
              <span className="tag tag-warn">{t("noTiers")}</span>
            )}
            {product.free_delivery && (
              <span className="tag tag-free">{t("common:freeDelivery")}</span>
            )}
            {product.colors.length > 0 && (
              <span className="tag">
                <span className={styles.dots} aria-hidden="true">
                  {product.colors.slice(0, 4).map((color) => (
                    <i key={color.id} style={{ background: color.hex }} />
                  ))}
                </span>
                {t("colors", { count: product.colors.length })}
              </span>
            )}
          </span>
        </span>
        <ChevronIcon size={18} className={styles.chevron} />
      </Link>
      <input
        type="checkbox"
        role="switch"
        className="switch"
        checked={visible}
        disabled={update.isPending}
        aria-label={`${t("showInStore")}: ${pick(product, "name", lang)}`}
        onChange={(event) =>
          update.mutate({ id: product.id, body: { is_visible: event.target.checked } })
        }
      />
      {update.isError && (
        <p className={`field-error ${styles.rowError}`} role="alert">
          {errorText(update.error)}
        </p>
      )}
    </li>
  );
}
