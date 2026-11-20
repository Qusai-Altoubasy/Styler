import type { CSSProperties } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";
import type { CategoryCard as Category } from "@styler/shared/api/types";
import { pick } from "@styler/shared/i18n/setup";
import { useLang } from "@styler/shared/i18n/useLang";
import { formatMoney } from "@styler/shared/utils/money";
import { PrintImage } from "../../ui/PrintImage";
import styles from "./CategoryCard.module.css";

export function CategoryCard({ category, index }: { category: Category; index: number }) {
  const { t } = useTranslation(["catalog", "common"]);
  const lang = useLang();
  const name = pick(category, "name", lang);
  const ink = category.color === "black" ? "key" : category.color;

  return (
    <Link
      to={`/products?category=${category.id}`}
      className={styles.card}
      style={{ "--cat": `var(--${ink})`, "--i": index } as CSSProperties}
    >
      <PrintImage src={category.image_url} alt="" ink={category.color} marks={false} />
      <div className={styles.body}>
        <h3>{name}</h3>
        <p className={styles.meta}>
          <span>{t("productCount", { count: category.product_count })}</span>
          <span className={styles.price}>
            {category.min_price ? (
              <>
                {t("common:from")}{" "}
                <span className="money">{formatMoney(category.min_price, lang)}</span>
              </>
            ) : (
              t("common:quote")
            )}
          </span>
        </p>
      </div>
    </Link>
  );
}
