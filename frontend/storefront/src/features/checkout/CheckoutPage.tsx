import { useQueryClient } from "@tanstack/react-query";
import { AnimatePresence, m } from "motion/react";
import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link, Navigate, useNavigate } from "react-router";
import { ApiError } from "@styler/shared/api/client";
import type { Governorate } from "@styler/shared/api/types";
import { pick } from "@styler/shared/i18n/setup";
import { useLang } from "@styler/shared/i18n/useLang";
import { formatMoney, toFils } from "@styler/shared/utils/money";
import { GOVERNORATE_NAMES } from "@styler/shared/utils/governorates";
import { isJordanMobile, normalizePhone } from "@styler/shared/utils/phone";
import { clearCart, useCart } from "../../lib/cart";
import { useResolvedCart } from "../../lib/resolvedCart";
import { useSettings } from "../../lib/settings";
import { computeTotals } from "../../lib/totals";
import { WhatsAppIcon } from "../../ui/icons";
import { LineDetails } from "../../ui/LineDetails";
import { useCreateOrder } from "./api";
import { saveLastOrder } from "./lastOrder";
import styles from "./CheckoutPage.module.css";

interface Form {
  name: string;
  phone: string;
  governorate: Governorate | "";
  address: string;
}
type Field = keyof Form;

const ITEM_ERRORS = new Set([
  "product_unavailable",
  "tier_required",
  "tier_not_found",
  "tier_not_allowed",
  "color_required",
  "color_not_found",
  "color_not_allowed",
  "approx_quantity_not_allowed",
]);

export function CheckoutPage() {
  const { t } = useTranslation(["checkout", "common"]);
  const lang = useLang();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const lines = useCart();
  const { resolved, hasUnavailable, totalsLines } = useResolvedCart(lines);
  const { data: settings } = useSettings();
  const createOrder = useCreateOrder();

  const [form, setForm] = useState<Form>({ name: "", phone: "", governorate: "", address: "" });
  const [touched, setTouched] = useState<Partial<Record<Field, boolean>>>({});
  const [submitted, setSubmitted] = useState(false);

  // Nothing to order (also right after an order, once the cart is cleared).
  if (lines.length === 0 && !createOrder.isSuccess) return <Navigate to="/cart" replace />;
  if (hasUnavailable) return <Navigate to="/cart" replace />;

  const errors: Partial<Record<Field, string>> = {};
  if (!form.name.trim()) errors.name = t("required");
  else if (form.name.trim().length > 100) errors.name = t("tooLong");
  if (!form.phone.trim()) errors.phone = t("required");
  else if (!isJordanMobile(form.phone)) errors.phone = t("phoneInvalid");
  if (!form.governorate) errors.governorate = t("required");
  if (!form.address.trim()) errors.address = t("required");
  else if (form.address.trim().length > 500) errors.address = t("tooLong");

  const show = (field: Field) => (submitted || touched[field] ? errors[field] : undefined);
  const set = (field: Field) => (e: { target: { value: string } }) =>
    setForm((f) => ({ ...f, [field]: e.target.value }));
  const blur = (field: Field) => () => setTouched((x) => ({ ...x, [field]: true }));

  const totals = computeTotals(totalsLines, settings, form.governorate || null);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    setSubmitted(true);
    if (Object.keys(errors).length > 0 || createOrder.isPending) {
      const first = (["name", "phone", "governorate", "address"] as Field[]).find((f) => errors[f]);
      if (first) document.getElementById(`checkout-${first}`)?.focus();
      return;
    }
    createOrder.mutate(
      {
        customer_name: form.name.trim(),
        phone: normalizePhone(form.phone),
        governorate: form.governorate as Governorate,
        address: form.address.trim(),
        items: lines.map((l) => ({
          product_id: l.productId,
          tier_id: l.tierId,
          color_id: l.colorId,
          approx_quantity: l.approxQuantity,
          item_count: l.itemCount,
        })),
      },
      {
        onSuccess: (order) => {
          saveLastOrder(order);
          clearCart();
          navigate(`/order/${order.id}`, { replace: true, state: { openWhatsApp: true } });
        },
        onError: (error) => {
          // A product changed since it was added: refresh them so the cart shows what.
          if (error instanceof ApiError && ITEM_ERRORS.has(error.code)) {
            void queryClient.invalidateQueries({ queryKey: ["product"] });
          }
        },
      },
    );
  };

  const error = createOrder.error;
  const errorText =
    error instanceof ApiError
      ? ITEM_ERRORS.has(error.code)
        ? t("errorItem")
        : error.status === 429
          ? t("errorTooMany", { minutes: Math.max(1, Math.ceil((error.retryAfter ?? 60) / 60)) })
          : error.code === "order_too_large"
            ? t("errorTooLarge")
            : error.status === 422
              ? t("errorInvalid")
              : t("errorNetwork")
      : error
        ? t("errorNetwork")
        : null;
  const itemError = error instanceof ApiError && ITEM_ERRORS.has(error.code);

  return (
    <div className={`page ${styles.layout}`}>
      <header className={styles.head}>
        <h1>{t("title")}</h1>
        <p className="muted">{t("intro")}</p>
      </header>

      <form className={styles.form} onSubmit={submit} noValidate>
        <Field id="checkout-name" label={t("name")} error={show("name")}>
          <input
            id="checkout-name"
            className="input"
            autoComplete="name"
            maxLength={100}
            value={form.name}
            onChange={set("name")}
            onBlur={blur("name")}
            aria-invalid={Boolean(show("name"))}
          />
        </Field>

        <Field id="checkout-phone" label={t("phone")} hint={t("phoneHint")} error={show("phone")}>
          <input
            id="checkout-phone"
            className="input"
            type="tel"
            inputMode="tel"
            autoComplete="tel-national"
            dir="ltr"
            maxLength={20}
            value={form.phone}
            onChange={set("phone")}
            onBlur={blur("phone")}
            aria-invalid={Boolean(show("phone"))}
          />
        </Field>

        <Field id="checkout-governorate" label={t("governorate")} error={show("governorate")}>
          <select
            id="checkout-governorate"
            className="input"
            value={form.governorate}
            onChange={set("governorate")}
            onBlur={blur("governorate")}
            aria-invalid={Boolean(show("governorate"))}
          >
            <option value="" disabled>
              {t("chooseGovernorate")}
            </option>
            {(settings?.governorates ?? []).map((g) => (
              <option key={g.governorate} value={g.governorate}>
                {GOVERNORATE_NAMES[g.governorate][lang]}
              </option>
            ))}
          </select>
        </Field>

        <Field
          id="checkout-address"
          label={t("address")}
          hint={t("addressHint")}
          error={show("address")}
        >
          <textarea
            id="checkout-address"
            className="input"
            autoComplete="street-address"
            maxLength={500}
            value={form.address}
            onChange={set("address")}
            onBlur={blur("address")}
            aria-invalid={Boolean(show("address"))}
          />
        </Field>

        <AnimatePresence>
          {errorText && (
            <m.div
              role="alert"
              className={styles.error}
              initial={{ opacity: 0, y: -6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
            >
              <p>{errorText}</p>
              {itemError && (
                <Link to="/cart" className="btn btn-sm">
                  {t("reviewCart")}
                </Link>
              )}
            </m.div>
          )}
        </AnimatePresence>

        <button
          type="submit"
          className={`btn btn-wa btn-block ${styles.submit}`}
          disabled={createOrder.isPending}
          aria-busy={createOrder.isPending}
        >
          {createOrder.isPending ? (
            <span className={styles.spinner} aria-hidden="true" />
          ) : (
            <WhatsAppIcon />
          )}
          {createOrder.isPending ? t("submitting") : t("submit")}
        </button>
        <p className={styles.after}>{t("afterSubmit")}</p>
      </form>

      <aside className={styles.summary}>
        <div className={styles.summaryHead}>
          <h2>{t("yourOrder")}</h2>
          <Link to="/cart">{t("edit")}</Link>
        </div>
        <ul className={styles.items}>
          {resolved.map((r) => (
            <li key={r.line.key}>
              <div>
                <b>{pick(r, "name", lang)}</b>
                {r.line.itemCount > 1 && (
                  <span className="muted ltr">
                    {" "}
                    {t("common:times", { count: r.line.itemCount })}
                  </span>
                )}
                <LineDetails tier={r.tier} color={r.color} approxQuantity={r.line.approxQuantity} />
              </div>
              <span className={styles.itemPrice}>
                {r.totals.unitPrice ? (
                  <span className="money">
                    {formatMoney(toFils(r.totals.unitPrice) * r.line.itemCount, lang)}
                  </span>
                ) : (
                  <span className="tag tag-quote">{t("common:awaitingQuote")}</span>
                )}
              </span>
            </li>
          ))}
        </ul>
        <dl className={styles.totals}>
          <div>
            <dt>{t("subtotal")}</dt>
            <dd className="money">{formatMoney(totals.subtotal, lang)}</dd>
          </div>
          <div>
            <dt>{t("delivery")}</dt>
            <dd>
              {totals.freeDelivery ? (
                <span className="tag tag-free">{t("deliveryFree")}</span>
              ) : totals.delivery === null ? (
                <small className="muted">{t("deliveryPick")}</small>
              ) : (
                <AnimatePresence mode="popLayout" initial={false}>
                  <m.span
                    key={totals.delivery}
                    className="money"
                    initial={{ y: 8, opacity: 0 }}
                    animate={{ y: 0, opacity: 1 }}
                    exit={{ y: -8, opacity: 0 }}
                  >
                    {formatMoney(totals.delivery, lang)}
                  </m.span>
                </AnimatePresence>
              )}
            </dd>
          </div>
          <div className={styles.grand}>
            <dt>{t("total")}</dt>
            <dd className="money">{formatMoney(totals.total, lang)}</dd>
          </div>
        </dl>
        {totals.awaitingQuote && <p className={styles.quoteNote}>{t("quoteNote")}</p>}
      </aside>
    </div>
  );
}

function Field({
  id,
  label,
  hint,
  error,
  children,
}: {
  id: string;
  label: string;
  hint?: string;
  error: string | undefined;
  children: React.ReactNode;
}) {
  return (
    <div className="field">
      <label htmlFor={id}>
        <span className={styles.label}>{label}</span>
      </label>
      {children}
      <AnimatePresence initial={false} mode="wait">
        {error ? (
          <m.small
            key="error"
            className="field-error"
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
          >
            {error}
          </m.small>
        ) : hint ? (
          <m.small key="hint" className="muted" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            {hint}
          </m.small>
        ) : null}
      </AnimatePresence>
    </div>
  );
}
