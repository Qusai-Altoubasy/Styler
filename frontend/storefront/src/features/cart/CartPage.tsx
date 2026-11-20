import { AnimatePresence, m } from "motion/react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";
import { pick } from "@styler/shared/i18n/setup";
import { useLang } from "@styler/shared/i18n/useLang";
import { formatMoney, toFils } from "@styler/shared/utils/money";
import { MAX_ITEM_COUNT, removeLine, setItemCount, useCart } from "../../lib/cart";
import { type ResolvedLine, useResolvedCart } from "../../lib/resolvedCart";
import { useSettings } from "../../lib/settings";
import { computeTotals } from "../../lib/totals";
import { BagIcon, TrashIcon } from "../../ui/icons";
import { LineDetails } from "../../ui/LineDetails";
import { useCategoryInk } from "../../lib/categories";
import { PrintImage } from "../../ui/PrintImage";
import { Stepper } from "../../ui/Stepper";
import styles from "./CartPage.module.css";

export function CartPage() {
  const { t } = useTranslation("cart");
  const lang = useLang();
  const lines = useCart();
  const { resolved, hasUnavailable, totalsLines } = useResolvedCart(lines);
  const { data: settings } = useSettings();
  const totals = computeTotals(totalsLines, settings, null);

  if (lines.length === 0) {
    return (
      <div className={`page ${styles.empty}`}>
        <m.div
          className={styles.emptyIcon}
          initial={{ rotate: -12, scale: 0.6, opacity: 0 }}
          animate={{ rotate: 0, scale: 1, opacity: 1 }}
          transition={{ type: "spring", stiffness: 260, damping: 16 }}
        >
          <BagIcon size={44} />
        </m.div>
        <h1>{t("empty")}</h1>
        <p className="muted">{t("emptyHint")}</p>
        <Link to="/products" className="btn btn-primary">
          {t("browse")}
        </Link>
      </div>
    );
  }

  return (
    <div className={`page ${styles.layout}`}>
      <section>
        <h1 className={styles.title}>{t("title")}</h1>
        <ul className={styles.lines}>
          <AnimatePresence initial={false}>
            {resolved.map((r) => (
              <CartRow key={r.line.key} r={r} />
            ))}
          </AnimatePresence>
        </ul>
      </section>

      <aside className={styles.summary} aria-label={t("summary")}>
        <h2>{t("summary")}</h2>
        <dl>
          <div>
            <dt>{t("subtotal")}</dt>
            <dd className="money">{formatMoney(totals.subtotal, lang)}</dd>
          </div>
          <div>
            <dt>{t("delivery")}</dt>
            <dd>
              {totals.freeDelivery ? (
                <span className="tag tag-free">{t("deliveryFree")}</span>
              ) : settings ? (
                <small>
                  {t("deliveryByZone", {
                    a: formatMoney(settings.zone_a_delivery_fee, lang),
                    b: formatMoney(settings.zone_b_delivery_fee, lang),
                  })}
                </small>
              ) : null}
            </dd>
          </div>
        </dl>
        {totals.awaitingQuote && <p className={styles.quoteNote}>{t("quoteNote")}</p>}
        {hasUnavailable && (
          <p className="field-error" role="alert">
            {t("fixUnavailable")}
          </p>
        )}
        {hasUnavailable ? (
          <button type="button" className="btn btn-primary btn-block" disabled>
            {t("checkout")}
          </button>
        ) : (
          <Link to="/checkout" className="btn btn-primary btn-block">
            {t("checkout")}
          </Link>
        )}
        <Link to="/products" className={`btn btn-block ${styles.keep}`}>
          {t("keepShopping")}
        </Link>
      </aside>
    </div>
  );
}

function CartRow({ r }: { r: ResolvedLine }) {
  const { t } = useTranslation(["cart", "common"]);
  const lang = useLang();
  const name = pick(r, "name", lang);
  const unavailable = r.status === "unavailable";
  const price = r.totals.unitPrice;
  const inkOf = useCategoryInk();

  return (
    <m.li
      layout
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, x: lang === "ar" ? -60 : 60, transition: { duration: 0.25 } }}
      transition={{ type: "spring", stiffness: 400, damping: 36 }}
      className={styles.row}
      data-unavailable={unavailable}
    >
      <Link to={`/products/${r.line.productId}`} className={styles.thumb}>
        <PrintImage
          src={r.image_url}
          alt=""
          ink={inkOf(r.categoryId ?? r.line.productId)}
          marks={false}
        />
      </Link>
      <div className={styles.info}>
        <Link to={`/products/${r.line.productId}`} className={styles.name}>
          {name}
        </Link>
        <LineDetails tier={r.tier} color={r.color} approxQuantity={r.line.approxQuantity} />
        {unavailable ? (
          <p className="field-error">{t("unavailable")}</p>
        ) : (
          <div className={styles.controls}>
            <Stepper
              size="sm"
              value={r.line.itemCount}
              onChange={(n) => setItemCount(r.line.key, n)}
              max={MAX_ITEM_COUNT}
              label={t("count")}
              decreaseLabel={t("decrease")}
              increaseLabel={t("increase")}
            />
            <span className={styles.linePrice}>
              {r.totals.pricingMode === "quote" ? (
                <span className="tag tag-quote">{t("common:awaitingQuote")}</span>
              ) : price ? (
                <span className="money">{formatMoney(toFils(price) * r.line.itemCount, lang)}</span>
              ) : null}
            </span>
          </div>
        )}
      </div>
      <button
        type="button"
        className={`icon-btn ${styles.remove}`}
        onClick={() => removeLine(r.line.key)}
        aria-label={t("remove", { name })}
      >
        <TrashIcon size={19} />
      </button>
    </m.li>
  );
}
