import { useTranslation } from "react-i18next";
import { useLang } from "@styler/shared/i18n/useLang";
import { formatMoney } from "@styler/shared/utils/money";
import { formatPhone } from "@styler/shared/utils/phone";
import { useSettings } from "../lib/settings";
import { FacebookIcon, InstagramIcon, WhatsAppIcon } from "../ui/icons";
import logo from "../logo.webp";
import styles from "./Footer.module.css";

export function Footer() {
  const { t } = useTranslation();
  const lang = useLang();
  const { data: settings } = useSettings();

  return (
    <footer id="contact" className={styles.footer}>
      <div className={`page ${styles.grid}`}>
        <section className={styles.about}>
          <img src={logo} alt="" width={64} height={64} />
          <h2>{t("brand")}</h2>
          <p className="muted">{t("onlineOnly")}</p>
        </section>

        <section>
          <h3>{t("contact")}</h3>
          <ul className={styles.links}>
            {settings && (
              <li>
                <a
                  href={`https://wa.me/${settings.whatsapp_international}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className={styles.wa}
                >
                  <WhatsAppIcon />
                  <span>
                    {t("whatsapp")}{" "}
                    <span className="ltr">{formatPhone(settings.whatsapp_number)}</span>
                  </span>
                </a>
              </li>
            )}
            {settings?.instagram_url && (
              <li>
                <a href={settings.instagram_url} target="_blank" rel="noopener noreferrer">
                  <InstagramIcon />
                  <span>{t("instagram")}</span>
                </a>
              </li>
            )}
            {settings?.facebook_url && (
              <li>
                <a href={settings.facebook_url} target="_blank" rel="noopener noreferrer">
                  <FacebookIcon />
                  <span>{t("facebook")}</span>
                </a>
              </li>
            )}
          </ul>
        </section>

        <section>
          <h3>{t("howTitle")}</h3>
          <ol className={styles.steps}>
            <li>{t("how1")}</li>
            <li>{t("how2")}</li>
            <li>{t("how3")}</li>
          </ol>
        </section>

        <section>
          <h3>{t("deliveryTitle")}</h3>
          {settings && (
            <dl className={styles.fees}>
              <div>
                <dt>{t("zoneA")}</dt>
                <dd className="money">{formatMoney(settings.zone_a_delivery_fee, lang)}</dd>
              </div>
              <div>
                <dt>{t("zoneB")}</dt>
                <dd className="money">{formatMoney(settings.zone_b_delivery_fee, lang)}</dd>
              </div>
            </dl>
          )}
        </section>
      </div>
      <div className={styles.inks} aria-hidden="true" />
      <p className={`page ${styles.bottom}`}>
        © {new Date().getFullYear()} {t("rights")}
      </p>
    </footer>
  );
}
