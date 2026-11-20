import { AnimatePresence, m } from "motion/react";
import { useEffect, useId, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router";
import { ApiError } from "@styler/shared/api/client";
import type { ProductDetail } from "@styler/shared/api/types";
import { pick, pickOptional } from "@styler/shared/i18n/setup";
import { useLang } from "@styler/shared/i18n/useLang";
import { digitsOnly } from "@styler/shared/utils/digits";
import { formatMoney, toFils } from "@styler/shared/utils/money";
import { LoadError } from "../../app/StatusPages";
import { addToCart, MAX_ITEM_COUNT } from "../../lib/cart";
import { BagIcon, CheckIcon, ChevronIcon, TruckIcon, WhatsAppIcon } from "../../ui/icons";
import { useCategoryInk } from "../../lib/categories";
import { PrintImage } from "../../ui/PrintImage";
import { Stepper } from "../../ui/Stepper";
import { useProduct } from "./api";
import styles from "./ProductPage.module.css";

export function ProductPage() {
  const { t } = useTranslation("product");
  const productId = Number(useParams().productId);
  const product = useProduct(productId);

  if (product.isError) {
    if (product.error instanceof ApiError && product.error.status === 404) {
      return (
        <div className={`page ${styles.missing}`}>
          <p>{t("notFound")}</p>
          <Link to="/products" className="btn btn-primary">
            {t("browse")}
          </Link>
        </div>
      );
    }
    return <LoadError onRetry={() => void product.refetch()} />;
  }
  if (!Number.isInteger(productId) || productId <= 0) {
    return (
      <div className={`page ${styles.missing}`}>
        <p>{t("notFound")}</p>
      </div>
    );
  }
  if (product.isPending) {
    return (
      <div className={`page ${styles.layout}`}>
        <div className={`skeleton ${styles.imageSkeleton}`} />
        <div className={styles.details}>
          <div className="skeleton" style={{ height: 40, width: "70%" }} />
          <div className="skeleton" style={{ height: 120 }} />
        </div>
      </div>
    );
  }
  // Keyed by id, so moving to another product starts from fresh choices.
  return <ProductView key={product.data.id} product={product.data} />;
}

function ProductView({ product }: { product: ProductDetail }) {
  const { t } = useTranslation(["product", "common"]);
  const lang = useLang();
  const id = useId();
  const name = pick(product, "name", lang);
  const description = pick(product, "description", lang);
  const isFixed = product.pricing_mode === "fixed";
  const inkOf = useCategoryInk();

  const [tierId, setTierId] = useState(isFixed ? (product.price_tiers[0]?.id ?? null) : null);
  // A color is required when the product has colors: the first one is preselected.
  const [colorId, setColorId] = useState(product.colors[0]?.id ?? null);
  const [approx, setApprox] = useState("");
  const [itemCount, setItemCount] = useState(1);
  const [state, setState] = useState<"idle" | "added" | "full">("idle");

  useEffect(() => {
    if (state !== "added") return;
    const timer = setTimeout(() => setState("idle"), 2200);
    return () => clearTimeout(timer);
  }, [state]);

  const tier = product.price_tiers.find((x) => x.id === tierId) ?? null;
  const color = product.colors.find((c) => c.id === colorId) ?? null;
  const approxQuantity = /^\d{1,7}$/.test(approx) && Number(approx) > 0 ? Number(approx) : null;

  const add = () => {
    const ok = addToCart({
      productId: product.id,
      tierId: isFixed ? tierId : null,
      colorId,
      approxQuantity: isFixed ? null : approxQuantity,
      itemCount,
      snapshot: {
        name_ar: product.name_ar,
        name_en: product.name_en,
        image_url: product.image_url,
        pricing_mode: product.pricing_mode,
        free_delivery: product.free_delivery,
        tier,
        color,
      },
    });
    setState(ok ? "added" : "full");
  };

  return (
    <div className={`page ${styles.layout}`}>
      <div className={styles.media}>
        <PrintImage src={product.image_url} alt={name} ink={inkOf(product.category.id)} eager />
      </div>

      <div className={styles.details}>
        <Link to={`/products?category=${product.category.id}`} className={styles.crumb}>
          {pick(product.category, "name", lang)}
          <ChevronIcon size={16} className={styles.crumbIcon} />
        </Link>
        <h1 className={styles.title}>{name}</h1>

        <div className={styles.priceRow}>
          {product.price ? (
            <span className={styles.price}>
              <small>{t("common:from")}</small>{" "}
              <span className="money">{formatMoney(product.price, lang)}</span>
            </span>
          ) : (
            <span className="tag tag-quote">{t("common:quote")}</span>
          )}
          {product.free_delivery && (
            <span className="tag tag-free">
              <TruckIcon size={14} /> {t("common:freeDelivery")}
            </span>
          )}
        </div>

        {description && <p className={styles.description}>{description}</p>}

        {isFixed ? (
          <fieldset className={styles.group}>
            <legend>{t("quantity")}</legend>
            <div className={styles.tiers} role="radiogroup">
              {product.price_tiers.map((x) => {
                const active = x.id === tierId;
                const note = pickOptional(x, "note", lang);
                return (
                  <button
                    key={x.id}
                    type="button"
                    role="radio"
                    aria-checked={active}
                    className={styles.tier}
                    onClick={() => setTierId(x.id)}
                  >
                    {active && (
                      <m.span
                        layoutId={`${id}-tier`}
                        className={styles.tierActive}
                        transition={{ type: "spring", stiffness: 480, damping: 34 }}
                      />
                    )}
                    <span className={styles.tierText}>
                      <b>{t("common:pieces", { count: x.quantity })}</b>
                      {note && <small>{note}</small>}
                    </span>
                    <span className={`${styles.tierPrice} money`}>
                      {formatMoney(x.price, lang)}
                    </span>
                  </button>
                );
              })}
            </div>
          </fieldset>
        ) : (
          <label className={`field ${styles.group}`}>
            <span>{t("approxQuantity")}</span>
            <input
              className="input"
              inputMode="numeric"
              dir="ltr"
              value={approx}
              onChange={(e) => setApprox(digitsOnly(e.target.value).slice(0, 7))}
            />
            <small className="muted">{t("approxHint")}</small>
          </label>
        )}

        {product.colors.length > 0 && (
          <fieldset className={styles.group}>
            <legend>
              {t("color")}
              {color && <span className={styles.colorName}>{pick(color, "name", lang)}</span>}
            </legend>
            <div className={styles.swatches} role="radiogroup">
              {product.colors.map((c) => (
                <button
                  key={c.id}
                  type="button"
                  role="radio"
                  aria-checked={c.id === colorId}
                  aria-label={pick(c, "name", lang)}
                  title={pick(c, "name", lang)}
                  className={styles.swatch}
                  style={{ background: c.hex }}
                  onClick={() => setColorId(c.id)}
                />
              ))}
            </div>
          </fieldset>
        )}

        <div className={styles.group}>
          <div className={styles.countRow}>
            <div>
              <span className={styles.label}>{t("itemCount")}</span>
              {isFixed && <small className="muted">{t("itemCountHint")}</small>}
            </div>
            <Stepper
              value={itemCount}
              onChange={setItemCount}
              max={MAX_ITEM_COUNT}
              label={t("itemCount")}
              decreaseLabel={t("decrease")}
              increaseLabel={t("increase")}
            />
          </div>
        </div>

        <div className={styles.note}>
          <WhatsAppIcon size={20} />
          <p>{t("designNote")}</p>
        </div>
        {product.free_delivery && (
          <div className={`${styles.note} ${styles.noteFree}`}>
            <TruckIcon size={20} />
            <p>{t("freeDeliveryNote")}</p>
          </div>
        )}

        <div className={styles.buy}>
          {isFixed && tier && (
            <div className={styles.total}>
              <span className="muted">{t("lineTotal")}</span>
              <AnimatePresence mode="popLayout" initial={false}>
                <m.b
                  key={`${tier.id}-${itemCount}`}
                  className="money"
                  initial={{ y: 10, opacity: 0 }}
                  animate={{ y: 0, opacity: 1 }}
                  exit={{ y: -10, opacity: 0 }}
                  transition={{ duration: 0.2 }}
                >
                  {formatMoney(toFils(tier.price) * itemCount, lang)}
                </m.b>
              </AnimatePresence>
            </div>
          )}
          <button
            type="button"
            className={`btn btn-primary ${styles.addBtn}`}
            onClick={add}
            data-state={state}
            disabled={isFixed && !tier}
          >
            <AnimatePresence mode="wait" initial={false}>
              <m.span
                key={state === "added" ? "added" : "add"}
                className={styles.addLabel}
                initial={{ y: 14, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                exit={{ y: -14, opacity: 0 }}
                transition={{ duration: 0.18 }}
              >
                {state === "added" ? <CheckIcon size={20} /> : <BagIcon size={20} />}
                {state === "added" ? t("added") : t("addToCart")}
              </m.span>
            </AnimatePresence>
          </button>
        </div>
        <AnimatePresence>
          {state === "added" && (
            <m.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className={styles.after}
            >
              <Link to="/cart" className="btn btn-block">
                {t("viewCart")}
              </Link>
            </m.div>
          )}
          {state === "full" && (
            <m.p
              role="alert"
              className="field-error"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
            >
              {t("cartFull")}
            </m.p>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
