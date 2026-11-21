import { describe, expect, it } from "vitest";
import type { AdminSettings } from "@styler/shared/api/types";
import { formFromSettings, isSocialLink, toSettingsUpdate, validateSettings } from "./settingsForm";

const saved: AdminSettings = {
  zone_a_delivery_fee: "2.000",
  zone_b_delivery_fee: "3.000",
  whatsapp_number: "0790087017",
  instagram_url: "https://www.instagram.com/styler_printing.press",
  facebook_url: null,
};

describe("settings form", () => {
  it("starts from the saved values and sends nothing when unchanged", () => {
    const form = formFromSettings(saved);
    expect(form.zoneA).toBe("2");
    expect(validateSettings(form)).toEqual({});
    expect(toSettingsUpdate(form, saved)).toEqual({});
  });

  it("sends only what changed, with Arabic digits converted", () => {
    const form = {
      ...formFromSettings(saved),
      zoneB: "٣٫٥",
      whatsapp: "٠٧٨ ١٢٣ ٤٥٦٧",
      instagram: " ",
    };
    expect(toSettingsUpdate(form, saved)).toEqual({
      zone_b_delivery_fee: "3.5",
      whatsapp_number: "0781234567",
      instagram_url: null,
    });
  });

  it("refuses bad fees, numbers and links", () => {
    const form = {
      zoneA: "-1",
      zoneB: "x",
      whatsapp: "0761234567",
      instagram: "http://instagram.com/x",
      facebook: "https://evil.com/facebook.com",
    };
    expect(validateSettings(form)).toEqual({
      zoneA: "invalidPrice",
      zoneB: "invalidPrice",
      whatsapp: "invalidPhone",
      instagram: "invalidInstagram",
      facebook: "invalidFacebook",
    });
  });

  it("accepts subdomains of the site only", () => {
    expect(isSocialLink("https://m.facebook.com/p", "facebook.com")).toBe(true);
    expect(isSocialLink("https://notfacebook.com/p", "facebook.com")).toBe(false);
    expect(isSocialLink("https://user:pw@facebook.com/p", "facebook.com")).toBe(false);
  });
});
