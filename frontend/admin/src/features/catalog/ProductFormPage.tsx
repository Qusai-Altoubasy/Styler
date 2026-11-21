import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router";
import type { AdminCategory, AdminProduct } from "@styler/shared/api/types";
import { LoadError, Loading } from "../../app/StatusPages";
import { useErrorText } from "../../lib/errors";
import { parseId } from "../../lib/numbers";
import { ConfirmButton } from "../../ui/ConfirmButton";
import { ImagePicker } from "../../ui/ImagePicker";
import { PageHead } from "../../ui/PageHead";
import { Segmented } from "../../ui/Segmented";
import { Switch } from "../../ui/Switch";
import { FieldError, TextField } from "../../ui/TextField";
import {
  useCategories,
  useCreateProduct,
  useDeleteProduct,
  useProduct,
  useUpdateProduct,
} from "./api";
import { ColorsEditor } from "./ColorsEditor";
import {
  formFromProduct,
  toCreate,
  toUpdate,
  validateProduct,
  type FormErrors,
  type ProductForm,
} from "./productForm";
import { CategoryOption } from "./ProductsTab";
import { TiersEditor } from "./TiersEditor";
import styles from "./forms.module.css";

export function ProductFormPage() {
  const { t } = useTranslation("catalog");
  const { productId } = useParams();
  // "new" (no id) or an id; anything else is shown as not found.
  const isNew = productId === undefined;
  const id = isNew ? null : parseId(productId);
  const categories = useCategories();
  const product = useProduct(id);

  if (categories.isPending || (id !== null && product.isPending)) return <Loading />;
  if (categories.isError) return <LoadError onRetry={() => void categories.refetch()} />;
  if (product.isError) return <LoadError onRetry={() => void product.refetch()} />;
  if (!isNew && (id === null || !product.data)) {
    return (
      <>
        <PageHead title={t("editProduct")} back="/products" />
        <p className="empty">{t("productNotFound")}</p>
      </>
    );
  }
  return (
    <ProductEditor key={id ?? "new"} product={product.data ?? null} categories={categories.data} />
  );
}

function ProductEditor({
  product,
  categories,
}: {
  product: AdminProduct | null;
  categories: AdminCategory[];
}) {
  const { t } = useTranslation("catalog");
  const errorText = useErrorText();
  const navigate = useNavigate();
  const create = useCreateProduct();
  const update = useUpdateProduct();
  const remove = useDeleteProduct();
  const save = product ? update : create;

  // A new product starts in the only category when there is just one.
  const [form, setForm] = useState<ProductForm>(() =>
    formFromProduct(product, categories.length === 1 ? (categories[0]?.id ?? null) : null),
  );
  const [errors, setErrors] = useState<FormErrors>({});
  const [tried, setTried] = useState(false);
  const [uploading, setUploading] = useState(false);

  const change = (patch: Partial<ProductForm>) => {
    const next = { ...form, ...patch };
    setForm(next);
    // After the first save attempt, marks clear as soon as a field is fixed.
    if (tried) setErrors(validateProduct(next));
  };
  const fieldError = (key: string) => {
    const error = errors[key];
    return error ? t(`fieldErrors.${error}`) : null;
  };

  const submit = () => {
    setTried(true);
    const found = validateProduct(form);
    setErrors(found);
    if (Object.keys(found).length > 0) {
      // Long form on a phone: bring the first field to fix into view.
      requestAnimationFrame(() => {
        const first = document.querySelector<HTMLElement>('form [aria-invalid="true"]');
        first?.scrollIntoView({ behavior: "smooth", block: "center" });
        first?.focus({ preventScroll: true });
      });
      return;
    }
    if (uploading) return;
    const done = { onSuccess: () => void navigate("/products") };
    if (product) update.mutate({ id: product.id, body: toUpdate(form, product) }, done);
    else create.mutate(toCreate(form), done);
  };

  const hasErrors = Object.keys(errors).length > 0;

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        submit();
      }}
      noValidate
    >
      <PageHead title={product ? t("editProduct") : t("newProduct")} back="/products" />

      <section className="card stack">
        <h2 className="card-title">{t("basics")}</h2>
        <label className="field">
          <span>{t("category")}</span>
          <select
            className="input"
            value={form.categoryId ?? ""}
            onChange={(event) =>
              change({ categoryId: event.target.value ? Number(event.target.value) : null })
            }
            aria-invalid={!!errors.categoryId}
          >
            <option value="" disabled>
              {t("chooseCategory")}
            </option>
            {categories.map((category) => (
              <CategoryOption key={category.id} category={category} />
            ))}
          </select>
          <FieldError text={fieldError("categoryId")} />
        </label>
        <div className="row-2">
          <TextField
            label={t("common:nameAr")}
            value={form.nameAr}
            onChange={(nameAr) => change({ nameAr })}
            dir="rtl"
            maxLength={200}
            error={fieldError("nameAr")}
          />
          <TextField
            label={t("common:nameEn")}
            value={form.nameEn}
            onChange={(nameEn) => change({ nameEn })}
            dir="ltr"
            maxLength={200}
            error={fieldError("nameEn")}
          />
        </div>
        <div className="row-2">
          <TextField
            label={t("descriptionAr")}
            optional={t("common:optional")}
            value={form.descriptionAr}
            onChange={(descriptionAr) => change({ descriptionAr })}
            dir="rtl"
            maxLength={5000}
            multiline
          />
          <TextField
            label={t("descriptionEn")}
            optional={t("common:optional")}
            value={form.descriptionEn}
            onChange={(descriptionEn) => change({ descriptionEn })}
            dir="ltr"
            maxLength={5000}
            multiline
          />
        </div>
        <div className="field">
          <span>{t("productImage")}</span>
          <ImagePicker
            value={form.image}
            onChange={(image) => change({ image })}
            onBusyChange={setUploading}
          />
        </div>
      </section>

      <section className="card stack">
        <h2 className="card-title">{t("pricing")}</h2>
        <Segmented
          label={t("pricing")}
          value={form.pricingMode}
          onChange={(pricingMode) => change({ pricingMode })}
          options={[
            { value: "fixed", label: t("modeFixed") },
            { value: "quote", label: t("modeQuote") },
          ]}
        />
        {form.pricingMode === "fixed" ? (
          <>
            <p className="muted">{t("fixedHint")}</p>
            <TiersEditor
              tiers={form.tiers}
              onChange={(tiers) => change({ tiers })}
              fieldError={fieldError}
            />
            {form.tiers.length === 0 && <p className={styles.warn}>{t("noTiersWarning")}</p>}
          </>
        ) : (
          <p className="muted">{t("quoteHint")}</p>
        )}
      </section>

      <section className="card stack">
        <h2 className="card-title">{t("colorsTitle")}</h2>
        <ColorsEditor
          hasColors={form.hasColors}
          colors={form.colors}
          onChange={(patch) => change(patch)}
          fieldError={fieldError}
        />
      </section>

      <section className="card">
        <h2 className="card-title">{t("options")}</h2>
        <Switch
          checked={form.freeDelivery}
          onChange={(freeDelivery) => change({ freeDelivery })}
          label={t("common:freeDelivery")}
          hint={t("freeDeliveryHint")}
        />
        <Switch
          checked={form.isVisible}
          onChange={(isVisible) => change({ isVisible })}
          label={t("visible")}
          hint={t("visibleHint")}
        />
      </section>

      <div className="save-bar">
        {hasErrors && <p className="form-status bad">{t("common:fixErrors")}</p>}
        {tried && uploading && <p className="form-status bad">{t("common:waitForImage")}</p>}
        {save.isError && (
          <p className="form-status bad" role="alert">
            {errorText(save.error)}
          </p>
        )}
        <button type="submit" className="btn btn-primary btn-block" disabled={save.isPending}>
          {save.isPending ? t("common:saving") : t("common:save")}
        </button>
      </div>

      {product && (
        <section className={`card ${styles.danger}`}>
          <p className="muted">{t("deleteHint")}</p>
          <ConfirmButton
            pending={remove.isPending}
            onConfirm={() =>
              remove.mutate(product.id, { onSuccess: () => void navigate("/products") })
            }
          >
            {t("deleteProduct")}
          </ConfirmButton>
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
