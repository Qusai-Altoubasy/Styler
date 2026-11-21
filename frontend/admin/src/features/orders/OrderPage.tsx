import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useLocation, useNavigate, useParams } from "react-router";
import type { OrderDetail, OrderItemOut, OrderStatus } from "@styler/shared/api/types";
import { pick, pickOptional } from "@styler/shared/i18n/setup";
import { useLang } from "@styler/shared/i18n/useLang";
import { GOVERNORATE_NAMES } from "@styler/shared/utils/governorates";
import { formatMoney, toFils, trimAmount } from "@styler/shared/utils/money";
import { formatPhone } from "@styler/shared/utils/phone";
import { LoadError, Loading } from "../../app/StatusPages";
import { formatDateTime } from "../../lib/dates";
import { isNotFound, useErrorText } from "../../lib/errors";
import { parseId, parseMoney } from "../../lib/numbers";
import { ConfirmButton } from "../../ui/ConfirmButton";
import { WhatsAppIcon } from "../../ui/icons";
import { PageHead } from "../../ui/PageHead";
import { Segmented } from "../../ui/Segmented";
import { useDeleteOrder, useOrder, useUpdateOrder } from "./api";
import styles from "./OrderPage.module.css";

export function OrderPage() {
  const { orderId } = useParams();
  const id = parseId(orderId);
  // Back to the log with the same search and filter.
  const back = `/orders${useLocation().search}`;
  // A mistyped address is "not found" right away, without asking the API.
  if (id === null) return <OrderNotFound id={orderId ?? ""} back={back} />;
  return <OrderLoader id={id} back={back} />;
}

function OrderLoader({ id, back }: { id: number; back: string }) {
  const order = useOrder(id);
  if (order.isPending) return <Loading />;
  if (order.isError) {
    if (isNotFound(order.error)) return <OrderNotFound id={String(id)} back={back} />;
    return <LoadError onRetry={() => void order.refetch()} />;
  }
  return <OrderView order={order.data} back={back} />;
}

function OrderNotFound({ id, back }: { id: string; back: string }) {
  const { t } = useTranslation("orders");
  return (
    <>
      <PageHead title={t("order", { id })} back={back} />
      <p className="empty">{t("common:errors.order_not_found")}</p>
    </>
  );
}

type Mark = OrderStatus | "none";

function OrderView({ order, back }: { order: OrderDetail; back: string }) {
  const { t } = useTranslation("orders");
  const lang = useLang();
  const errorText = useErrorText();
  const navigate = useNavigate();
  const markUpdate = useUpdateOrder(order.id);
  const remove = useDeleteOrder(order.id);
  const quoteItems = order.items.filter((item) => item.pricing_mode === "quote");

  // While the mark saves, show the new choice already.
  const mark: Mark = markUpdate.isPending
    ? (markUpdate.variables.status ?? "none")
    : (order.status ?? "none");

  return (
    <>
      <PageHead title={t("order", { id: order.id })} back={back} />
      <p className={`muted ${styles.date}`}>{formatDateTime(order.created_at, lang)}</p>

      <section className="card stack">
        <h2 className="card-title">{t("mark")}</h2>
        <Segmented<Mark>
          label={t("mark")}
          value={mark}
          disabled={markUpdate.isPending}
          onChange={(next) => markUpdate.mutate({ status: next === "none" ? null : next })}
          options={[
            { value: "none", label: t("markNone") },
            { value: "done", label: t("markDone") },
            { value: "cancelled", label: t("markCancelled") },
          ]}
        />
        <small className="muted">{t("markHint")}</small>
        {markUpdate.isError && (
          <p className="field-error" role="alert">
            {errorText(markUpdate.error)}
          </p>
        )}
      </section>

      <section className="card stack">
        <h2 className="card-title">{t("customer")}</h2>
        <dl className={styles.details}>
          <dt>{t("name")}</dt>
          <dd>{order.customer_name}</dd>
          <dt>{t("phone")}</dt>
          <dd>
            <a href={`tel:${order.phone}`} className="ltr">
              {formatPhone(order.phone)}
            </a>
          </dd>
          <dt>{t("governorate")}</dt>
          <dd>{GOVERNORATE_NAMES[order.governorate][lang]}</dd>
          <dt>{t("address")}</dt>
          <dd className={styles.address}>{order.address}</dd>
        </dl>
        <a
          className="btn btn-wa btn-block"
          href={`https://wa.me/${order.whatsapp_number}`}
          target="_blank"
          rel="noreferrer"
        >
          <WhatsAppIcon size={20} />
          {t("openWhatsapp")}
        </a>
      </section>

      <section className="card">
        <h2 className="card-title">{t("items")}</h2>
        <ul className={styles.items}>
          {order.items.map((item) => (
            <ItemLine key={item.id} item={item} />
          ))}
        </ul>
        {quoteItems.length > 0 && <QuotePrices order={order} items={quoteItems} />}
        <Totals order={order} />
      </section>

      <NoteSection order={order} />

      <section className="card stack">
        <p className="muted">{t("deleteHint")}</p>
        <ConfirmButton
          pending={remove.isPending}
          onConfirm={() => remove.mutate(undefined, { onSuccess: () => void navigate(back) })}
        >
          {t("deleteOrder")}
        </ConfirmButton>
        {remove.isError && (
          <p className="field-error" role="alert">
            {errorText(remove.error)}
          </p>
        )}
      </section>
    </>
  );
}

function ItemLine({ item }: { item: OrderItemOut }) {
  const { t } = useTranslation("orders");
  const lang = useLang();
  const note = pickOptional(item, "tier_note", lang);
  const color = pickOptional(item, "color_name", lang);
  return (
    <li className={styles.item}>
      <div className={styles.itemText}>
        <strong>{pick(item, "product_name", lang)}</strong>
        <span className="muted">
          {item.quantity !== null &&
            (item.pricing_mode === "fixed"
              ? t("pieces", { count: item.quantity })
              : t("approxQty", { count: item.quantity }))}
          {note && ` · ${note}`}
        </span>
        {color && (
          <span className={styles.color}>
            <i style={{ background: item.color_hex ?? undefined }} aria-hidden="true" />
            {color}
          </span>
        )}
        <span className="muted">{t("times", { count: item.item_count })}</span>
      </div>
      <div className={styles.itemPrice}>
        {item.line_total !== null ? (
          <span className="money">{formatMoney(item.line_total, lang)}</span>
        ) : (
          <span className="tag tag-quote">{t("awaitingQuote")}</span>
        )}
      </div>
    </li>
  );
}

/** The price of each quote item, per piece. The server recomputes subtotal and total. */
function QuotePrices({ order, items }: { order: OrderDetail; items: OrderItemOut[] }) {
  const { t } = useTranslation("orders");
  const lang = useLang();
  const errorText = useErrorText();
  const update = useUpdateOrder(order.id);
  const initial = () =>
    Object.fromEntries(
      items.map((item) => [item.id, item.unit_price ? trimAmount(item.unit_price) : ""]),
    );
  const [prices, setPrices] = useState<Record<number, string>>(initial);
  const [tried, setTried] = useState(false);

  const invalid = (id: number) => {
    const typed = prices[id]?.trim() ?? "";
    return typed !== "" && parseMoney(typed) === null;
  };
  const changed = items.filter((item) => {
    const typed = prices[item.id]?.trim() ?? "";
    const value = typed === "" ? null : parseMoney(typed);
    const saved = item.unit_price === null ? null : trimAmount(item.unit_price);
    return value !== saved;
  });

  return (
    <form
      className={styles.quote}
      noValidate
      onSubmit={(event) => {
        event.preventDefault();
        setTried(true);
        if (items.some((item) => invalid(item.id)) || changed.length === 0) return;
        update.mutate(
          {
            item_prices: changed.map((item) => {
              const typed = prices[item.id]?.trim() ?? "";
              return { item_id: item.id, unit_price: typed === "" ? null : parseMoney(typed) };
            }),
          },
          { onSuccess: () => setTried(false) },
        );
      }}
    >
      {items.map((item) => {
        const value = parseMoney(prices[item.id] ?? "");
        return (
          <label key={item.id} className="field">
            <span>
              {pick(item, "product_name", lang)} · {t("unitPrice")}
            </span>
            <input
              className="input"
              inputMode="decimal"
              dir="ltr"
              value={prices[item.id] ?? ""}
              onChange={(event) => setPrices({ ...prices, [item.id]: event.target.value })}
              aria-invalid={tried && invalid(item.id)}
            />
            {tried && invalid(item.id) ? (
              <small className="field-error">{t("invalidPrice")}</small>
            ) : (
              <small className="muted">
                {value !== null && item.item_count > 1
                  ? t("lineTotal", {
                      total: formatMoney(toFils(value) * item.item_count, lang),
                    })
                  : t("unitPriceHint", { count: item.item_count })}
              </small>
            )}
          </label>
        );
      })}
      {update.isError && (
        <p className="field-error" role="alert">
          {errorText(update.error)}
        </p>
      )}
      {update.isSuccess && changed.length === 0 && (
        <p className="form-status ok" role="status">
          {t("pricesSaved")}
        </p>
      )}
      <button
        type="submit"
        className="btn btn-primary btn-block"
        disabled={update.isPending || changed.length === 0}
      >
        {update.isPending ? t("common:saving") : t("savePrices")}
      </button>
    </form>
  );
}

function Totals({ order }: { order: OrderDetail }) {
  const { t } = useTranslation("orders");
  const lang = useLang();
  const free = toFils(order.delivery_fee) === 0;
  return (
    <>
      <dl className={styles.totals}>
        <dt>{t("subtotal")}</dt>
        <dd className="money">{formatMoney(order.subtotal, lang)}</dd>
        <dt>{t("delivery")}</dt>
        <dd className="money">{free ? t("free") : formatMoney(order.delivery_fee, lang)}</dd>
        <dt className={styles.grand}>{t("total")}</dt>
        <dd className={`money ${styles.grand}`}>{formatMoney(order.total, lang)}</dd>
      </dl>
      {order.awaiting_quote && <p className={styles.awaiting}>{t("totalAwaiting")}</p>}
    </>
  );
}

function NoteSection({ order }: { order: OrderDetail }) {
  const { t } = useTranslation("orders");
  const errorText = useErrorText();
  const update = useUpdateOrder(order.id);
  const [note, setNote] = useState(order.internal_note ?? "");
  const unchanged = note.trim() === (order.internal_note ?? "");

  return (
    <form
      className="card stack"
      onSubmit={(event) => {
        event.preventDefault();
        if (!unchanged) update.mutate({ internal_note: note.trim() || null });
      }}
    >
      <label className="field">
        <span className="card-title">{t("note")}</span>
        <small className="muted">{t("noteHint")}</small>
        <textarea
          className="input"
          value={note}
          onChange={(event) => setNote(event.target.value)}
          maxLength={2000}
          rows={3}
        />
      </label>
      {update.isError && (
        <p className="field-error" role="alert">
          {errorText(update.error)}
        </p>
      )}
      {update.isSuccess && unchanged && (
        <p className="form-status ok" role="status">
          {t("common:saved")}
        </p>
      )}
      <button type="submit" className="btn btn-block" disabled={update.isPending || unchanged}>
        {update.isPending ? t("common:saving") : t("saveNote")}
      </button>
    </form>
  );
}
