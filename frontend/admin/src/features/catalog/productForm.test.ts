import { describe, expect, it } from "vitest";
import type { AdminProduct } from "@styler/shared/api/types";
import {
  emptyColor,
  emptyTier,
  formFromProduct,
  toCreate,
  toUpdate,
  validateProduct,
  type ProductForm,
} from "./productForm";

const product: AdminProduct = {
  id: 7,
  category_id: 3,
  name_ar: "ستيكر",
  name_en: "Sticker",
  description_ar: "",
  description_en: "",
  image_key: "media/a.webp",
  image_url: "/media/a.webp",
  pricing_mode: "fixed",
  free_delivery: false,
  is_visible: true,
  shown_in_store: true,
  price: "7.000",
  price_tiers: [{ id: 11, quantity: 250, price: "7.000", note_ar: "4 سم", note_en: null }],
  colors: [{ id: 21, name_ar: "أحمر", name_en: "Red", hex: "#ff0000" }],
  created_at: "2026-11-20T08:00:00Z",
  updated_at: "2026-11-20T08:00:00Z",
};

function validForm(): ProductForm {
  const form = formFromProduct(null, 3);
  form.nameAr = " كوب ";
  form.nameEn = "Mug";
  form.tiers = [{ ...emptyTier(), quantity: "١٠", price: "٢٫٥" }];
  return form;
}

describe("validateProduct", () => {
  it("accepts a complete form with Arabic digits", () => {
    expect(validateProduct(validForm())).toEqual({});
  });

  it("needs both names and a category", () => {
    const form = { ...validForm(), nameAr: " ", nameEn: "", categoryId: null };
    expect(validateProduct(form)).toEqual({
      nameAr: "required",
      nameEn: "required",
      categoryId: "required",
    });
  });

  it("checks quantities and prices, and finds a repeated tier", () => {
    const form = validForm();
    const bad = { ...emptyTier(), quantity: "0", price: "1.2345" };
    const twin = { ...emptyTier(), quantity: "10", price: "3" };
    form.tiers.push(bad, twin);
    expect(validateProduct(form)).toEqual({
      [`tier.${bad.uid}.quantity`]: "invalidCount",
      [`tier.${bad.uid}.price`]: "invalidPrice",
      [`tier.${twin.uid}.quantity`]: "duplicateTier",
    });
  });

  it("lets the same quantity repeat with a different note", () => {
    const form = validForm();
    form.tiers.push({ ...emptyTier(), quantity: "10", price: "3", noteAr: "6 سم" });
    expect(validateProduct(form)).toEqual({});
  });

  it("ignores tiers of a quote product, and colors when they are off", () => {
    const form = { ...validForm(), pricingMode: "quote" as const, tiers: [emptyTier()] };
    form.colors = [emptyColor()];
    expect(validateProduct(form)).toEqual({});
    form.hasColors = true;
    expect(Object.values(validateProduct(form))).toEqual(["required", "required"]);
  });
});

describe("payloads", () => {
  it("builds a new product with ASCII numbers and empty notes as null", () => {
    const body = toCreate(validForm());
    expect(body).toMatchObject({
      category_id: 3,
      name_ar: "كوب",
      image_key: null,
      price_tiers: [{ quantity: 10, price: "2.5", note_ar: null, note_en: null }],
      colors: [],
    });
    expect(body.price_tiers?.[0]).not.toHaveProperty("id");
  });

  it("keeps row ids on edit and leaves an unchanged image out", () => {
    const body = toUpdate(formFromProduct(product, null), product);
    expect(body).not.toHaveProperty("image_key");
    expect(body.price_tiers).toEqual([
      { id: 11, quantity: 250, price: "7", note_ar: "4 سم", note_en: null },
    ]);
    expect(body.colors).toEqual([{ id: 21, name_ar: "أحمر", name_en: "Red", hex: "#ff0000" }]);
  });

  it("sends a removed image as null and a new one as its key", () => {
    const form = formFromProduct(product, null);
    form.image = { key: null, url: null };
    expect(toUpdate(form, product).image_key).toBeNull();
    form.image = { key: "tmp/b.webp", url: "blob:x" };
    expect(toUpdate(form, product).image_key).toBe("tmp/b.webp");
  });

  it("keeps a quote product's old tiers by not sending them, and clears colors when off", () => {
    const form = { ...formFromProduct(product, null), pricingMode: "quote" as const };
    form.hasColors = false;
    const body = toUpdate(form, product);
    expect(body).not.toHaveProperty("price_tiers");
    expect(body.colors).toEqual([]);
  });
});
