import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useErrorText } from "../../lib/errors";
import { useLogin } from "../../lib/session";
import { PasswordInput } from "../../ui/PasswordInput";
import styles from "./LoginPage.module.css";

/** One password, no username. The session cookie then lasts 30 days on this device. */
export function LoginPage() {
  const { t } = useTranslation("auth");
  const errorText = useErrorText();
  const login = useLogin();
  const [password, setPassword] = useState("");

  return (
    <main className={`page ${styles.wrap}`}>
      <form
        className={`card ${styles.card}`}
        onSubmit={(event) => {
          event.preventDefault();
          // Sent exactly as typed: a password is never trimmed.
          if (password) login.mutate(password);
        }}
      >
        <div className={styles.inks} aria-hidden="true">
          <span />
          <span />
          <span />
          <span />
        </div>
        <h1>{t("title")}</h1>
        <p className="muted">{t("intro")}</p>
        <label className="field">
          <span>{t("password")}</span>
          <PasswordInput
            value={password}
            onChange={setPassword}
            autoComplete="current-password"
            autoFocus
            invalid={login.isError}
            showLabel={t("show")}
            hideLabel={t("hide")}
          />
        </label>
        {login.isError && (
          <p className="field-error" role="alert">
            {errorText(login.error)}
          </p>
        )}
        <button
          type="submit"
          className="btn btn-primary btn-block"
          disabled={login.isPending || !password}
        >
          {login.isPending ? t("submitting") : t("submit")}
        </button>
      </form>
    </main>
  );
}
