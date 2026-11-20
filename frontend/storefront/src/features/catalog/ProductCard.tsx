import { m } from "motion/react";
import type { Ref } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";
import type { BrandColor, ProductCard as Product } from "@styler/shared/api/types";
import { pick } from "@styler/shared/i18n/setup";
import { useLang } from "@styler/shared/i18n/useLang";
import { formatMoney } from "@styler/shared/utils/money";
import { TruckIcon } from "../../ui/icons";
import { PrintImage } from "../../ui/PrintImage";
import styles from "./ProductCard.module.css";

/** `ref` is passed on to the list item so AnimatePresence's popLayout can measure it. */
export function ProductCard({
  product,
  ink,
  ref,
}: {
  product: Product;
  ink: BrandColor;
  ref?: Ref<HTMLLIElement>;
}) {
  const { t } = useTranslation(["catalog", "common"]);
  const lang = useLang();
  const name = pick(product, "name", lang);

  return (
    <m.li
      ref={ref}
      layout
      initial={{ opacity: 0, scale: 0.94 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.94 }}
      transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
      className={styles.item}
    >
      <Link to={`/products/${product.id}`} className={styles.card}>
        <PrintImage src={product.image_url} alt={name} ink={ink} />
        <div className={styles.body}>
          <h3>{name}</h3>
          <p className={styles.price}>
            {product.price ? (
              <>
                <small>{t("common:from")}</small>{" "}
                <span className="money">{formatMoney(product.price, lang)}</span>
              </>
            ) : (
              <span className="tag tag-quote">{t("common:quote")}</span>
            )}
          </p>
          <div className={styles.tags}>
            {product.free_delivery && (
              <span className="tag tag-free">
                <TruckIcon size={14} /> {t("common:freeDelivery")}
              </span>
            )}
            {product.has_colors && (
              <span className={styles.inks} title={t("inColors")}>
                <span className="visually-hidden">{t("inColors")}</span>
              </span>
            )}
          </div>
        </div>
      </Link>
    </m.li>
  );
}
