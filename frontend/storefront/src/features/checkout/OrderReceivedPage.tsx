import { m } from "motion/react";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useLocation, useNavigate, useParams } from "react-router";
import { pick } from "@styler/shared/i18n/setup";
import { useLang } from "@styler/shared/i18n/useLang";
import { formatMoney } from "@styler/shared/utils/money";
import { useSettings } from "../../lib/settings";
import { WhatsAppIcon } from "../../ui/icons";
import { LineDetails } from "../../ui/LineDetails";
import { readLastOrder } from "./lastOrder";
import { buildOrderMessage, whatsappUrl } from "./message";
import styles from "./OrderReceivedPage.module.css";

export function OrderReceivedPage() {
  const { t } = useTranslation(["checkout", "common"]);
  const lang = useLang();
  const orderId = Number(useParams().orderId);
  const location = useLocation();
  const navigate = useNavigate();
  const { data: settings } = useSettings();
  const [order] = useState(() => readLastOrder(orderId));
  const opened = useRef(false);
  const [opening, setOpening] = useState(false);

  const url =
    order && settings
      ? whatsappUrl(settings.whatsapp_international, buildOrderMessage(order, lang))
      : null;
  const shouldOpen = (location.state as { openWhatsApp?: boolean } | null)?.openWhatsApp === true;

  // Right after ordering: let the confirmation show for a moment, then open WhatsApp.
  // The state is cleared first, so a refresh or coming back never opens it twice.
  // Clearing it re-runs this effect, so the timer is only cancelled on unmount.
  const timer = useRef<number | undefined>(undefined);
  useEffect(() => {
    if (!shouldOpen || !url || opened.current) return;
    opened.current = true;
    navigate(location.pathname, { replace: true, state: null });
    setOpening(true);
    timer.current = window.setTimeout(() => {
      setOpening(false);
      window.location.href = url;
    }, 1100);
  }, [shouldOpen, url, navigate, location.pathname]);
  useEffect(
    () => () => {
      window.clearTimeout(timer.current);
      opened.current = false;
    },
    [],
  );

  return (
    <div className={`page ${styles.page}`}>
      {order && <Stamp />}
      <h1 className={styles.title}>{order ? t("receivedTitle") : t("receivedMissingTitle")}</h1>
      <div className={styles.number}>
        <span className="muted">{t("orderNumber")}</span>
        <m.b
          className="ltr"
          initial={{ letterSpacing: "0.4em", opacity: 0 }}
          animate={{ letterSpacing: "0.02em", opacity: 1 }}
          transition={{ delay: 0.5, duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
        >
          {Number.isInteger(orderId) ? orderId : ""}
        </m.b>
      </div>

      {order ? (
        <>
          <p className={styles.next}>{t("receivedNext")}</p>
          {url && (
            <a
              href={url}
              className={`btn btn-wa ${styles.resend}`}
              target="_blank"
              rel="noopener noreferrer"
            >
              <WhatsAppIcon />
              {t("resend")}
            </a>
          )}
          <p className={styles.hint} aria-live="polite">
            {opening ? t("opening") : t("resendHint")}
          </p>

          <section className={styles.receipt}>
            <ul>
              {order.items.map((item) => (
                <li key={item.id}>
                  <div>
                    <b>
                      {pick(
                        { name_ar: item.product_name_ar, name_en: item.product_name_en },
                        "name",
                        lang,
                      )}
                    </b>
                    {item.item_count > 1 && (
                      <span className="muted ltr">
                        {" "}
                        {t("common:times", { count: item.item_count })}
                      </span>
                    )}
                    <LineDetails
                      tier={
                        item.pricing_mode === "fixed" && item.quantity !== null
                          ? {
                              quantity: item.quantity,
                              note_ar: item.tier_note_ar,
                              note_en: item.tier_note_en,
                            }
                          : null
                      }
                      color={
                        item.color_hex
                          ? {
                              name_ar: item.color_name_ar,
                              name_en: item.color_name_en,
                              hex: item.color_hex,
                            }
                          : null
                      }
                      approxQuantity={item.pricing_mode === "quote" ? item.quantity : null}
                    />
                  </div>
                  <span className={styles.price}>
                    {item.line_total !== null ? (
                      <span className="money">{formatMoney(item.line_total, lang)}</span>
                    ) : (
                      <span className="tag tag-quote">{t("common:awaitingQuote")}</span>
                    )}
                  </span>
                </li>
              ))}
            </ul>
            <dl>
              <div>
                <dt>{t("delivery")}</dt>
                <dd className="money">
                  {Number(order.delivery_fee) === 0
                    ? t("deliveryFree")
                    : formatMoney(order.delivery_fee, lang)}
                </dd>
              </div>
              <div className={styles.grand}>
                <dt>{t("total")}</dt>
                <dd className="money">{formatMoney(order.total, lang)}</dd>
              </div>
            </dl>
            {order.awaiting_quote && <p className="muted">{t("quoteNote")}</p>}
          </section>
        </>
      ) : (
        <>
          <p className={styles.next}>{t("receivedMissing")}</p>
          {settings && (
            <a
              href={`https://wa.me/${settings.whatsapp_international}`}
              className={`btn btn-wa ${styles.resend}`}
              target="_blank"
              rel="noopener noreferrer"
            >
              <WhatsAppIcon />
              {t("contactWhatsapp")}
            </a>
          )}
        </>
      )}

      <Link to="/" className={styles.home}>
        {t("backHome")}
      </Link>
    </div>
  );
}

/** A registration target that turns into a check mark: the order is in register. */
function Stamp() {
  const draw = { hidden: { pathLength: 0, opacity: 0 }, shown: { pathLength: 1, opacity: 1 } };
  return (
    <m.svg
      className={styles.stamp}
      viewBox="0 0 100 100"
      initial="hidden"
      animate="shown"
      aria-hidden="true"
    >
      <m.circle
        cx="50"
        cy="50"
        r="44"
        fill="none"
        stroke="var(--cyan)"
        strokeWidth="5"
        variants={draw}
        transition={{ duration: 0.6, ease: "easeOut" }}
        style={{ rotate: -90 }}
      />
      <m.circle
        cx="50"
        cy="50"
        r="44"
        fill="none"
        stroke="var(--magenta)"
        strokeWidth="5"
        strokeDasharray="0 1"
        initial={{ x: 5, y: -4, opacity: 0.8 }}
        animate={{ x: 0, y: 0, opacity: 0 }}
        transition={{ delay: 0.35, duration: 0.6 }}
      />
      <m.path
        d="M28 52 L44 67 L73 36"
        fill="none"
        stroke="var(--key)"
        strokeWidth="7"
        strokeLinecap="round"
        strokeLinejoin="round"
        variants={draw}
        transition={{ delay: 0.45, duration: 0.45, ease: "easeOut" }}
      />
    </m.svg>
  );
}
