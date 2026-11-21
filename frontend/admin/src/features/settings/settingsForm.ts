import type { AdminSettings, SettingsUpdate } from "@styler/shared/api/types";
import { trimAmount } from "@styler/shared/utils/money";
import { isJordanMobile, normalizePhone } from "@styler/shared/utils/phone";
import { parseMoney } from "../../lib/numbers";

export interface SettingsForm {
  zoneA: string;
  zoneB: string;
  whatsapp: string;
  instagram: string;
  facebook: string;
}

export type SettingsError =
  "invalidPrice" | "invalidPhone" | "invalidInstagram" | "invalidFacebook";
export type SettingsErrors = Partial<Record<keyof SettingsForm, SettingsError>>;

export function formFromSettings(settings: AdminSettings): SettingsForm {
  return {
    zoneA: trimAmount(settings.zone_a_delivery_fee),
    zoneB: trimAmount(settings.zone_b_delivery_fee),
    whatsapp: settings.whatsapp_number,
    instagram: settings.instagram_url ?? "",
    facebook: settings.facebook_url ?? "",
  };
}

/** The same rule as the API: an https link on the site's own domain (or a subdomain). */
export function isSocialLink(text: string, domain: string): boolean {
  let url: URL;
  try {
    url = new URL(text);
  } catch {
    return false;
  }
  if (url.protocol !== "https:" || url.username || url.password || /\s/.test(text)) return false;
  return url.hostname === domain || url.hostname.endsWith(`.${domain}`);
}

export function validateSettings(form: SettingsForm): SettingsErrors {
  const errors: SettingsErrors = {};
  if (parseMoney(form.zoneA) === null) errors.zoneA = "invalidPrice";
  if (parseMoney(form.zoneB) === null) errors.zoneB = "invalidPrice";
  if (!isJordanMobile(form.whatsapp)) errors.whatsapp = "invalidPhone";
  const instagram = form.instagram.trim();
  if (instagram && !isSocialLink(instagram, "instagram.com")) errors.instagram = "invalidInstagram";
  const facebook = form.facebook.trim();
  if (facebook && !isSocialLink(facebook, "facebook.com")) errors.facebook = "invalidFacebook";
  return errors;
}

/** Only what changed; an emptied link is sent as null to remove it. */
export function toSettingsUpdate(form: SettingsForm, saved: AdminSettings): SettingsUpdate {
  const body: SettingsUpdate = {};
  const zoneA = parseMoney(form.zoneA);
  const zoneB = parseMoney(form.zoneB);
  if (zoneA !== null && zoneA !== trimAmount(saved.zone_a_delivery_fee)) {
    body.zone_a_delivery_fee = zoneA;
  }
  if (zoneB !== null && zoneB !== trimAmount(saved.zone_b_delivery_fee)) {
    body.zone_b_delivery_fee = zoneB;
  }
  const whatsapp = normalizePhone(form.whatsapp);
  if (whatsapp !== saved.whatsapp_number) body.whatsapp_number = whatsapp;
  const instagram = form.instagram.trim() || null;
  if (instagram !== saved.instagram_url) body.instagram_url = instagram;
  const facebook = form.facebook.trim() || null;
  if (facebook !== saved.facebook_url) body.facebook_url = facebook;
  return body;
}
