import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router";
import type { AdminCategory, BrandColor, CategoryCreate } from "@styler/shared/api/types";
import { LoadError, Loading } from "../../app/StatusPages";
import { useErrorText } from "../../lib/errors";
import { parseId } from "../../lib/numbers";
import { ConfirmButton } from "../../ui/ConfirmButton";
import { ImagePicker, type ImageValue } from "../../ui/ImagePicker";
import { inkVar } from "@styler/shared/theme/ink";
import { PageHead } from "../../ui/PageHead";
import { useCategories, useDeleteCategory, useSaveCategory } from "./api";
import styles from "./forms.module.css";

const INKS: { color: BrandColor; label: string }[] = [
  { color: "cyan", label: "inkCyan" },
  { color: "magenta", label: "inkMagenta" },
  { color: "yellow", label: "inkYellow" },
  { color: "black", label: "inkBlack" },
];

export function CategoryFormPage() {
  const { t } = useTranslation("catalog");
  const { categoryId } = useParams();
  const categories = useCategories();
  const isNew = categoryId === undefined;
  const id = isNew ? null : parseId(categoryId);

  if (categories.isPending) return <Loading />;
  if (categories.isError) return <LoadError onRetry={() => void categories.refetch()} />;
  const category = isNew ? null : categories.data.find((item) => item.id === id);
  if (category === undefined) {
    return (
      <>
        <PageHead title={t("editCategory")} back="/products" />
        <p className="empty">{t("categoryNotFound")}</p>
      </>
    );
  }
  // Keyed, so opening another category starts from its own values.
  return <CategoryForm key={category?.id ?? "new"} category={category} />;
}

function CategoryForm({ category }: { category: AdminCategory | null }) {
  const { t } = useTranslation("catalog");
  const errorText = useErrorText();
  const navigate = useNavigate();
  const save = useSaveCategory(category?.id ?? null);
  const remove = useDeleteCategory(category?.id ?? 0);

  const [nameAr, setNameAr] = useState(category?.name_ar ?? "");
  const [nameEn, setNameEn] = useState(category?.name_en ?? "");
  const [color, setColor] = useState<BrandColor>(category?.color ?? "cyan");
  const [image, setImage] = useState<ImageValue>({
    key: category?.image_key ?? null,
    url: category?.image_url ?? null,
  });
  const [uploading, setUploading] = useState(false);
  const [tried, setTried] = useState(false);

  const missingAr = !nameAr.trim();
  const missingEn = !nameEn.trim();

  const submit = () => {
    setTried(true);
    if (missingAr || missingEn || uploading) return;
    const body: CategoryCreate = {
      name_ar: nameAr.trim(),
      name_en: nameEn.trim(),
      color,
      sort_order: category?.sort_order ?? 0,
    };
    // An edit leaves the image out unless it changed (a new upload, or removed).
    const imageChanged = image.key !== (category?.image_key ?? null);
    save.mutate(category === null || imageChanged ? { ...body, image_key: image.key } : body, {
      onSuccess: () => void navigate("/products"),
    });
  };

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        submit();
      }}
      noValidate
    >
      <PageHead title={category ? t("editCategory") : t("newCategory")} back="/products" />
      <section className="card stack">
        <div className="row-2">
          <label className="field">
            <span>{t("common:nameAr")}</span>
            <input
              className="input"
              value={nameAr}
              onChange={(event) => setNameAr(event.target.value)}
              maxLength={100}
              dir="rtl"
              aria-invalid={tried && missingAr}
            />
            {tried && missingAr && (
              <small className="field-error">{t("fieldErrors.required")}</small>
            )}
          </label>
          <label className="field">
            <span>{t("common:nameEn")}</span>
            <input
              className="input"
              value={nameEn}
              onChange={(event) => setNameEn(event.target.value)}
              maxLength={100}
              dir="ltr"
              aria-invalid={tried && missingEn}
            />
            {tried && missingEn && (
              <small className="field-error">{t("fieldErrors.required")}</small>
            )}
          </label>
        </div>

        <fieldset className={styles.fieldset}>
          <legend>{t("categoryColor")}</legend>
          <div className={styles.inks} role="radiogroup">
            {INKS.map((ink) => (
              <label key={ink.color} className={styles.ink}>
                <input
                  type="radio"
                  name="color"
                  checked={color === ink.color}
                  onChange={() => setColor(ink.color)}
                />
                <span
                  className={styles.inkSwatch}
                  style={{ background: ink.color === "black" ? "#16171b" : inkVar(ink.color) }}
                />
                {t(ink.label)}
              </label>
            ))}
          </div>
        </fieldset>

        <div className="field">
          <span>
            {t("categoryImage")} <small>({t("common:optional")})</small>
          </span>
          <small className="muted">{t("categoryImageHint")}</small>
          <ImagePicker value={image} onChange={setImage} onBusyChange={setUploading} />
        </div>
      </section>

      <div className="save-bar">
        {save.isError && (
          <p className="form-status bad" role="alert">
            {errorText(save.error)}
          </p>
        )}
        {tried && uploading && <p className="form-status bad">{t("common:waitForImage")}</p>}
        <button type="submit" className="btn btn-primary btn-block" disabled={save.isPending}>
          {save.isPending ? t("common:saving") : t("common:save")}
        </button>
      </div>

      {category && (
        <section className={`card ${styles.danger}`}>
          {category.product_count > 0 ? (
            <p className="muted">{t("deleteCategoryBlocked")}</p>
          ) : (
            <ConfirmButton
              pending={remove.isPending}
              onConfirm={() =>
                remove.mutate(undefined, { onSuccess: () => void navigate("/products") })
              }
            >
              {t("deleteCategory")}
            </ConfirmButton>
          )}
          {remove.isError && (
            <p className="field-error" role="alert">
              {errorText(remove.error)}
            </p>
          )}
        </section>
      )}
    </form>
  );
}
