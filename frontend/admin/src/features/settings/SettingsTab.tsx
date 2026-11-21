import { useState } from "react";
import { useTranslation } from "react-i18next";
import type { AdminSettings } from "@styler/shared/api/types";
import { LoadError, Loading } from "../../app/StatusPages";
import { useErrorText } from "../../lib/errors";
import { useChangePassword, useLogout } from "../../lib/session";
import { LogoutIcon } from "../../ui/icons";
import { PasswordInput } from "../../ui/PasswordInput";
import { TextField } from "../../ui/TextField";
import { useSaveSettings, useSettings } from "./api";
import {
  formFromSettings,
  toSettingsUpdate,
  validateSettings,
  type SettingsErrors,
  type SettingsForm,
} from "./settingsForm";

export function SettingsTab() {
  const settings = useSettings();
  return (
    <>
      {settings.isPending ? (
        <Loading />
      ) : settings.isError ? (
        <LoadError onRetry={() => void settings.refetch()} />
      ) : (
        <StoreSettings saved={settings.data} />
      )}
      <PasswordSection />
      <LogoutSection />
    </>
  );
}

function StoreSettings({ saved }: { saved: AdminSettings }) {
  const { t } = useTranslation("settings");
  const errorText = useErrorText();
  const save = useSaveSettings();
  const [form, setForm] = useState<SettingsForm>(() => formFromSettings(saved));
  const [errors, setErrors] = useState<SettingsErrors>({});
  const [note, setNote] = useState<"saved" | "nothingChanged" | null>(null);

  const change = (patch: Partial<SettingsForm>) => {
    setForm({ ...form, ...patch });
    setNote(null);
  };
  const error = (key: keyof SettingsForm) => {
    const found = errors[key];
    return found ? t(`errors.${found}`) : null;
  };

  return (
    <form
      noValidate
      onSubmit={(event) => {
        event.preventDefault();
        const found = validateSettings(form);
        setErrors(found);
        if (Object.keys(found).length > 0) return;
        const body = toSettingsUpdate(form, saved);
        if (Object.keys(body).length === 0) return setNote("nothingChanged");
        save.mutate(body, {
          onSuccess: (next) => {
            setForm(formFromSettings(next));
            setNote("saved");
          },
        });
      }}
    >
      <section className="card stack">
        <h2 className="card-title">{t("delivery")}</h2>
        <p className="card-hint">{t("deliveryHint")}</p>
        <div className="row-2">
          <TextField
            label={t("zoneA")}
            value={form.zoneA}
            onChange={(zoneA) => change({ zoneA })}
            inputMode="decimal"
            dir="ltr"
            error={error("zoneA")}
          />
          <TextField
            label={t("zoneB")}
            value={form.zoneB}
            onChange={(zoneB) => change({ zoneB })}
            inputMode="decimal"
            dir="ltr"
            error={error("zoneB")}
          />
        </div>
      </section>

      <section className="card stack">
        <h2 className="card-title">{t("contact")}</h2>
        <TextField
          label={t("whatsapp")}
          hint={t("whatsappHint")}
          value={form.whatsapp}
          onChange={(whatsapp) => change({ whatsapp })}
          inputMode="numeric"
          type="tel"
          dir="ltr"
          maxLength={20}
          error={error("whatsapp")}
        />
        <TextField
          label={t("instagram")}
          hint={t("linkHint")}
          value={form.instagram}
          onChange={(instagram) => change({ instagram })}
          type="url"
          dir="ltr"
          maxLength={500}
          error={error("instagram")}
        />
        <TextField
          label={t("facebook")}
          hint={t("linkHint")}
          value={form.facebook}
          onChange={(facebook) => change({ facebook })}
          type="url"
          dir="ltr"
          maxLength={500}
          error={error("facebook")}
        />
        {save.isError && (
          <p className="form-status bad" role="alert">
            {errorText(save.error)}
          </p>
        )}
        {note && (
          <p className={`form-status ${note === "saved" ? "ok" : ""}`} role="status">
            {note === "saved" ? t("common:saved") : t("nothingChanged")}
          </p>
        )}
        <button type="submit" className="btn btn-primary btn-block" disabled={save.isPending}>
          {save.isPending ? t("common:saving") : t("common:save")}
        </button>
      </section>
    </form>
  );
}

function PasswordSection() {
  const { t } = useTranslation("settings");
  const errorText = useErrorText();
  const change = useChangePassword();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [again, setAgain] = useState("");
  const [tried, setTried] = useState(false);

  const tooShort = next.length < 8;
  const mismatch = again !== next;

  return (
    <form
      className="card stack"
      noValidate
      onSubmit={(event) => {
        event.preventDefault();
        setTried(true);
        if (!current || tooShort || mismatch) return;
        // Passwords go exactly as typed: never trimmed or converted.
        change.mutate(
          { current_password: current, new_password: next },
          {
            onSuccess: () => {
              setCurrent("");
              setNext("");
              setAgain("");
              setTried(false);
            },
          },
        );
      }}
    >
      <h2 className="card-title">{t("password")}</h2>
      <p className="card-hint">{t("passwordHint")}</p>
      <label className="field">
        <span>{t("currentPassword")}</span>
        <PasswordInput
          value={current}
          onChange={setCurrent}
          autoComplete="current-password"
          invalid={tried && !current}
          showLabel={t("show")}
          hideLabel={t("hide")}
        />
        {tried && !current && <small className="field-error">{t("errors.required")}</small>}
      </label>
      <label className="field">
        <span>{t("newPassword")}</span>
        <small className="muted">{t("newPasswordHint")}</small>
        <PasswordInput
          value={next}
          onChange={setNext}
          autoComplete="new-password"
          invalid={tried && tooShort}
          showLabel={t("show")}
          hideLabel={t("hide")}
        />
        {tried && tooShort && <small className="field-error">{t("errors.tooShort")}</small>}
      </label>
      <label className="field">
        <span>{t("confirmPassword")}</span>
        <PasswordInput
          value={again}
          onChange={setAgain}
          autoComplete="new-password"
          invalid={tried && mismatch}
          showLabel={t("show")}
          hideLabel={t("hide")}
        />
        {tried && mismatch && <small className="field-error">{t("errors.mismatch")}</small>}
      </label>
      {change.isError && (
        <p className="form-status bad" role="alert">
          {errorText(change.error)}
        </p>
      )}
      {change.isSuccess && (
        <p className="form-status ok" role="status">
          {t("passwordChanged")}
        </p>
      )}
      <button type="submit" className="btn btn-block" disabled={change.isPending}>
        {change.isPending ? t("common:saving") : t("changePassword")}
      </button>
    </form>
  );
}

/** One logout, and it logs out every device (also what to press for a lost phone). */
function LogoutSection() {
  const { t } = useTranslation("settings");
  const errorText = useErrorText();
  const logout = useLogout();
  return (
    <section className="card stack">
      <h2 className="card-title">{t("logout")}</h2>
      <p className="card-hint">{t("logoutHint")}</p>
      {logout.isError && (
        <p className="form-status bad" role="alert">
          {errorText(logout.error)}
        </p>
      )}
      <button
        type="button"
        className="btn btn-danger btn-block"
        disabled={logout.isPending}
        onClick={() => logout.mutate()}
      >
        <LogoutIcon size={18} />
        {logout.isPending ? t("loggingOut") : t("logoutButton")}
      </button>
    </section>
  );
}
