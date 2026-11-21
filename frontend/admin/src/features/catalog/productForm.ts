import type {
  AdminProduct,
  ColorIn,
  PricingMode,
  PriceTierIn,
  ProductCreate,
  ProductUpdate,
} from "@styler/shared/api/types";
import { trimAmount } from "@styler/shared/utils/money";
import { parseCount, parseMoney } from "../../lib/numbers";
import type { ImageValue } from "../../ui/ImagePicker";

/** One quantity row as typed: text until it is checked. `id` keeps an existing row's id. */
export interface TierRow {
  uid: string;
  id: number | null;
  quantity: string;
  price: string;
  noteAr: string;
  noteEn: string;
}

export interface ColorRow {
  uid: string;
  id: number | null;
  nameAr: string;
  nameEn: string;
  hex: string;
}

export interface ProductForm {
  categoryId: number | null;
  nameAr: string;
  nameEn: string;
  descriptionAr: string;
  descriptionEn: string;
  image: ImageValue;
  pricingMode: PricingMode;
  tiers: TierRow[];
  hasColors: boolean;
  colors: ColorRow[];
  freeDelivery: boolean;
  isVisible: boolean;
}

/** Message keys (in the `catalog` namespace) for each field that needs fixing. */
export type FormErrors = Record<string, FieldError>;
export type FieldError = "required" | "invalidCount" | "invalidPrice" | "duplicateTier";

let nextUid = 0;
const uid = () => `row-${++nextUid}`;

export const DEFAULT_COLOR = "#0093cf";

export function emptyTier(): TierRow {
  return { uid: uid(), id: null, quantity: "", price: "", noteAr: "", noteEn: "" };
}

export function emptyColor(hex = DEFAULT_COLOR): ColorRow {
  return { uid: uid(), id: null, nameAr: "", nameEn: "", hex };
}

export function formFromProduct(
  product: AdminProduct | null,
  categoryId: number | null,
): ProductForm {
  if (!product) {
    return {
      categoryId,
      nameAr: "",
      nameEn: "",
      descriptionAr: "",
      descriptionEn: "",
      image: { key: null, url: null },
      pricingMode: "fixed",
      tiers: [emptyTier()],
      hasColors: false,
      colors: [],
      freeDelivery: false,
      isVisible: true,
    };
  }
  return {
    categoryId: product.category_id,
    nameAr: product.name_ar,
    nameEn: product.name_en,
    descriptionAr: product.description_ar,
    descriptionEn: product.description_en,
    image: { key: product.image_key, url: product.image_url },
    pricingMode: product.pricing_mode,
    tiers: product.price_tiers.map((tier) => ({
      uid: uid(),
      id: tier.id,
      quantity: String(tier.quantity),
      price: trimAmount(tier.price),
      noteAr: tier.note_ar ?? "",
      noteEn: tier.note_en ?? "",
    })),
    hasColors: product.colors.length > 0,
    colors: product.colors.map((color) => ({
      uid: uid(),
      id: color.id,
      nameAr: color.name_ar,
      nameEn: color.name_en,
      hex: color.hex,
    })),
    freeDelivery: product.free_delivery,
    isVisible: product.is_visible,
  };
}

/** What must be fixed before saving; empty when the form can be sent. */
export function validateProduct(form: ProductForm): FormErrors {
  const errors: FormErrors = {};
  if (form.categoryId === null) errors.categoryId = "required";
  if (!form.nameAr.trim()) errors.nameAr = "required";
  if (!form.nameEn.trim()) errors.nameEn = "required";

  // Tiers are only checked (and sent) for fixed prices; a quote product keeps its old rows.
  if (form.pricingMode === "fixed") {
    const seen = new Set<string>();
    for (const tier of form.tiers) {
      const quantity = parseCount(tier.quantity);
      if (quantity === null) errors[`tier.${tier.uid}.quantity`] = "invalidCount";
      if (parseMoney(tier.price) === null) errors[`tier.${tier.uid}.price`] = "invalidPrice";
      const same = `${quantity}|${tier.noteAr.trim()}|${tier.noteEn.trim()}`;
      if (quantity !== null && seen.has(same))
        errors[`tier.${tier.uid}.quantity`] = "duplicateTier";
      seen.add(same);
    }
  }

  if (form.hasColors) {
    if (form.colors.length === 0) errors.colors = "required";
    for (const color of form.colors) {
      if (!color.nameAr.trim()) errors[`color.${color.uid}.nameAr`] = "required";
      if (!color.nameEn.trim()) errors[`color.${color.uid}.nameEn`] = "required";
    }
  }
  return errors;
}

function tiersIn(form: ProductForm): PriceTierIn[] {
  return form.tiers.map((tier) => ({
    ...(tier.id !== null && { id: tier.id }),
    quantity: parseCount(tier.quantity) ?? 0,
    price: parseMoney(tier.price) ?? "",
    note_ar: tier.noteAr.trim() || null,
    note_en: tier.noteEn.trim() || null,
  }));
}

function colorsIn(form: ProductForm): ColorIn[] {
  if (!form.hasColors) return [];
  return form.colors.map((color) => ({
    ...(color.id !== null && { id: color.id }),
    name_ar: color.nameAr.trim(),
    name_en: color.nameEn.trim(),
    hex: color.hex.toLowerCase(),
  }));
}

/** Fields that are the same for a new product and an edit. */
function commonFields(form: ProductForm) {
  return {
    category_id: form.categoryId ?? 0,
    name_ar: form.nameAr.trim(),
    name_en: form.nameEn.trim(),
    description_ar: form.descriptionAr.trim(),
    description_en: form.descriptionEn.trim(),
    pricing_mode: form.pricingMode,
    free_delivery: form.freeDelivery,
    is_visible: form.isVisible,
    colors: colorsIn(form),
  };
}

/** Call after `validateProduct` found nothing. */
export function toCreate(form: ProductForm): ProductCreate {
  return {
    ...commonFields(form),
    image_key: form.image.key,
    price_tiers: form.pricingMode === "fixed" ? tiersIn(form) : [],
  };
}

/**
 * An edit sends every field except: the image when it did not change (its key is the
 * stored one), and the quantity table for a quote product (its old rows stay, so
 * switching back to a fixed price brings them back).
 */
export function toUpdate(form: ProductForm, original: AdminProduct): ProductUpdate {
  return {
    ...commonFields(form),
    ...(form.image.key !== original.image_key && { image_key: form.image.key }),
    ...(form.pricingMode === "fixed" && { price_tiers: tiersIn(form) }),
  };
}
