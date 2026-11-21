import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";
import { LoadError } from "../../app/StatusPages";
import { useCategories } from "../../lib/categories";
import { CategoryCard } from "./CategoryCard";
import { InkTitle } from "./InkTitle";
import styles from "./HomePage.module.css";

/** The heading's ink intro plays once per visit to the site, not on every return home. */
let introPlayed = false;

export function HomePage() {
  const { t } = useTranslation("catalog");
  const categories = useCategories();
  const [replay] = useState(() => introPlayed);
  useEffect(() => {
    introPlayed = true;
  }, []);

  return (
    <div className={replay ? styles.replay : undefined}>
      <section className={`page ${styles.hero}`}>
        <InkTitle text={t("heroTitle")} still={replay} />
        <p className={styles.intro}>{t("heroIntro")}</p>
        <span className={styles.target} aria-hidden="true" />
      </section>

      <section className="page" aria-labelledby="categories-heading">
        <div className={styles.sectionHead}>
          <h2 id="categories-heading">{t("categories")}</h2>
          <Link to="/products" className="btn btn-sm">
            {t("allProducts")}
          </Link>
        </div>

        {categories.isError ? (
          <LoadError onRetry={() => void categories.refetch()} />
        ) : categories.isPending ? (
          <div className={styles.grid}>
            {Array.from({ length: 6 }, (_, i) => (
              <div key={i} className={`skeleton ${styles.skeleton}`} />
            ))}
          </div>
        ) : categories.data.length === 0 ? (
          <p className="muted">{t("noCategories")}</p>
        ) : (
          <div className={styles.grid}>
            {categories.data.map((category, index) => (
              <CategoryCard key={category.id} category={category} index={index} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
