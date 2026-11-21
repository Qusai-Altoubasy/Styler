import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useSearchParams } from "react-router";
import type { MarkFilter, OrderRow, OrderStatus } from "@styler/shared/api/types";
import { pick } from "@styler/shared/i18n/setup";
import { useLang } from "@styler/shared/i18n/useLang";
import { GOVERNORATE_NAMES } from "@styler/shared/utils/governorates";
import { formatMoney } from "@styler/shared/utils/money";
import { formatPhone } from "@styler/shared/utils/phone";
import { LoadError, Loading } from "../../app/StatusPages";
import { formatDateTime } from "../../lib/dates";
import { useDebounced } from "../../lib/useDebounced";
import { LoadMore } from "../../ui/LoadMore";
import { SearchBox } from "../../ui/SearchBox";
import { Segmented } from "../../ui/Segmented";
import { useOrders, useOrderStats } from "./api";
import styles from "./OrdersTab.module.css";

const FILTERS: readonly MarkFilter[] = ["all", "unmarked", "done", "cancelled"];
const FILTER_LABELS: Record<MarkFilter, string> = {
  all: "filterAll",
  unmarked: "filterUnmarked",
  done: "filterDone",
  cancelled: "filterCancelled",
};

export function OrdersTab() {
  return (
    <>
      <Stats />
      <OrdersLog />
    </>
  );
}

function Stats() {
  const { t } = useTranslation("orders");
  const lang = useLang();
  const stats = useOrderStats();
  const value = (n: number | string | undefined) => (stats.data ? n : "—");
  return (
    <section className={styles.stats} aria-busy={stats.isPending}>
      <Stat label={t("statAll")} value={value(stats.data?.all_orders)} />
      <Stat label={t("statToday")} value={value(stats.data?.today_orders)} />
      <Stat label={t("statQuote")} value={value(stats.data?.quote_orders)} />
      <Stat
        label={t("statValue")}
        hint={t("statValueHint")}
        value={stats.data ? formatMoney(stats.data.orders_value, lang) : "—"}
        money
      />
    </section>
  );
}

function Stat({
  label,
  value,
  hint,
  money = false,
}: {
  label: string;
  value: number | string | undefined;
  hint?: string;
  money?: boolean;
}) {
  return (
    <div className={styles.stat}>
      <span className={styles.statLabel}>{label}</span>
      <strong className={money ? "money" : "ltr"}>{value}</strong>
      {hint && <small className="muted">{hint}</small>}
    </div>
  );
}

/** The log, with its search and filter kept in the address so "back" returns to them. */
function OrdersLog() {
  const { t } = useTranslation("orders");
  const [params, setParams] = useSearchParams();
  const statusParam = params.get("status") as MarkFilter | null;
  const status: MarkFilter = statusParam && FILTERS.includes(statusParam) ? statusParam : "all";
  const [q, setQ] = useState(params.get("q") ?? "");
  const debouncedQ = useDebounced(q);

  useEffect(() => {
    setParams(
      (current) => {
        const next = new URLSearchParams(current);
        if (debouncedQ.trim()) next.set("q", debouncedQ.trim());
        else next.delete("q");
        return next;
      },
      { replace: true },
    );
  }, [debouncedQ, setParams]);

  const orders = useOrders(status, debouncedQ);
  const items = orders.data?.pages.flatMap((page) => page.items) ?? [];
  const total = orders.data?.pages[0]?.total ?? 0;

  return (
    <section className="card">
      <div className={styles.filters}>
        <SearchBox value={q} onChange={setQ} placeholder={t("search")} />
        <Segmented
          label={t("filter")}
          value={status}
          onChange={(next) =>
            setParams(
              (current) => {
                const updated = new URLSearchParams(current);
                if (next === "all") updated.delete("status");
                else updated.set("status", next);
                return updated;
              },
              { replace: true },
            )
          }
          options={FILTERS.map((value) => ({ value, label: t(FILTER_LABELS[value]) }))}
        />
      </div>

      {orders.isPending ? (
        <Loading />
      ) : orders.isError ? (
        <LoadError onRetry={() => void orders.refetch()} />
      ) : items.length === 0 ? (
        <p className="empty">
          {debouncedQ.trim() || status !== "all" ? t("noMatch") : t("noOrders")}
        </p>
      ) : (
        <>
          <OrdersTable items={items} busy={orders.isPlaceholderData} />
          <LoadMore
            shown={items.length}
            total={total}
            loading={orders.isFetchingNextPage}
            onMore={() => void orders.fetchNextPage()}
          />
        </>
      )}
    </section>
  );
}

/** A real table on wide screens; on phones each row folds into a card (CSS only). */
function OrdersTable({ items, busy }: { items: OrderRow[]; busy: boolean }) {
  const { t } = useTranslation("orders");
  const lang = useLang();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const back = params.toString();

  return (
    <table className={styles.table} aria-busy={busy}>
      <thead>
        <tr>
          <th>{t("colNumber")}</th>
          <th>{t("colDate")}</th>
          <th>{t("colCustomer")}</th>
          <th>{t("colPhone")}</th>
          <th>{t("colGovernorate")}</th>
          <th>{t("colProducts")}</th>
          <th>{t("colTotal")}</th>
          <th>{t("colMark")}</th>
        </tr>
      </thead>
      <tbody>
        {items.map((order) => {
          const to = { pathname: `/orders/${order.id}`, search: back ? `?${back}` : "" };
          return (
            <tr
              key={order.id}
              className={styles.row}
              data-status={order.status ?? "none"}
              onClick={() => void navigate(to)}
            >
              <td className={styles.number}>
                <Link to={to} className="ltr" onClick={(event) => event.stopPropagation()}>
                  {order.id}
                </Link>
              </td>
              <td className={styles.date}>{formatDateTime(order.created_at, lang)}</td>
              <td className={styles.customer}>{order.customer_name}</td>
              <td className={styles.phone}>
                <span className="ltr">{formatPhone(order.phone)}</span>
              </td>
              <td className={styles.governorate}>{GOVERNORATE_NAMES[order.governorate][lang]}</td>
              <td className={styles.products}>
                {order.products
                  .map((line) => `${pick(line, "product_name", lang)} ×${line.item_count}`)
                  .join(lang === "ar" ? "، " : ", ")}
              </td>
              <td className={styles.total}>
                <span className="money">{formatMoney(order.total, lang)}</span>
                {order.awaiting_quote && (
                  <span className="tag tag-quote">{t("awaitingQuote")}</span>
                )}
              </td>
              <td className={styles.mark}>
                <MarkTag status={order.status} />
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

export function MarkTag({ status }: { status: OrderStatus | null }) {
  const { t } = useTranslation("orders");
  if (status === "done") return <span className="tag tag-done">{t("markDone")}</span>;
  if (status === "cancelled")
    return <span className="tag tag-cancelled">{t("markCancelled")}</span>;
  return null;
}
