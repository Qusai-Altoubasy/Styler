import { describe, expect, it } from "vitest";
import type { OrderConfirmation } from "@styler/shared/api/types";
import { buildOrderMessage, whatsappUrl } from "./message";

const base = {
  id: 1005,
  created_at: "2026-11-16T10:00:00Z",
  customer_name: "أحمد",
  phone: "0791234567",
  governorate: "irbid",
  address: "شارع الجامعة",
} as const;

const fixedItem = {
  id: 1,
  product_id: 7,
  product_name_ar: "ستيكر دائري",
  product_name_en: "Round sticker",
  pricing_mode: "fixed",
  quantity: 250,
  tier_note_ar: "4 سم",
  tier_note_en: "4 cm",
  color_name_ar: null,
  color_name_en: null,
  color_hex: null,
  item_count: 2,
  unit_price: "7.000",
  line_total: "14.000",
} as const;

const quoteItem = {
  ...fixedItem,
  id: 2,
  product_name_ar: "بنر فليكس",
  product_name_en: "Flex banner",
  pricing_mode: "quote",
  quantity: 3,
  tier_note_ar: null,
  item_count: 1,
  color_name_ar: "أسود",
  color_name_en: "Black",
  unit_price: null,
  line_total: null,
} as const;

describe("buildOrderMessage", () => {
  it("lists a mixed order with the server's numbers", () => {
    const order: OrderConfirmation = {
      ...base,
      items: [fixedItem, quoteItem],
      delivery_fee: "3.000",
      subtotal: "14.000",
      total: "17.000",
      awaiting_quote: true,
    };
    expect(buildOrderMessage(order, "ar")).toBe(
      [
        "مرحباً Styler، بدي أطلب:",
        "رقم الطلب: 1005",
        "",
        "الاسم: أحمد",
        "الهاتف: 0791234567",
        "المحافظة: إربد",
        "العنوان: شارع الجامعة",
        "",
        "المنتجات:",
        "1) ستيكر دائري",
        "   الكمية: 250 قطعة (4 سم)",
        "   العدد: 2",
        "   السعر: 14 د.أ",
        "2) بنر فليكس",
        "   كمية تقريبية: 3",
        "   اللون: أسود",
        "   السعر: عرض سعر (بانتظار التسعير)",
        "",
        "التوصيل: 3 د.أ",
        "الإجمالي: 17 د.أ",
        "(الإجمالي لا يشمل المنتجات التي بانتظار التسعير)",
      ].join("\n"),
    );
  });

  it("says free delivery and leaves out the quote note when everything is priced", () => {
    const text = buildOrderMessage(
      {
        ...base,
        items: [
          {
            ...fixedItem,
            item_count: 1,
            quantity: 1,
            tier_note_ar: null,
            tier_note_en: null,
            line_total: "7.000",
          },
        ],
        delivery_fee: "0.000",
        subtotal: "7.000",
        total: "7.000",
        awaiting_quote: false,
      },
      "ar",
    );
    expect(text).toContain("الكمية: قطعة واحدة\n");
    expect(text).toContain("التوصيل: مجاني");
    expect(text).not.toContain("بانتظار");
  });

  it("follows the page language in English", () => {
    const order: OrderConfirmation = {
      ...base,
      items: [fixedItem, quoteItem],
      delivery_fee: "3.000",
      subtotal: "14.000",
      total: "17.000",
      awaiting_quote: true,
    };
    expect(buildOrderMessage(order, "en")).toBe(
      [
        "Hello Styler, I'd like to order:",
        "Order number: 1005",
        "",
        "Name: أحمد",
        "Phone: 0791234567",
        "Governorate: Irbid",
        "Address: شارع الجامعة",
        "",
        "Products:",
        "1) Round sticker",
        "   Quantity: 250 pieces (4 cm)",
        "   How many: 2",
        "   Price: 14 JOD",
        "2) Flex banner",
        "   Approximate quantity: 3",
        "   Color: Black",
        "   Price: quote (awaiting a price)",
        "",
        "Delivery: 3 JOD",
        "Total: 17 JOD",
        "(The total does not include products awaiting a price)",
      ].join("\n"),
    );
  });

  it("never mentions payment, in either language", () => {
    const order: OrderConfirmation = {
      ...base,
      items: [fixedItem],
      delivery_fee: "2.000",
      subtotal: "14.000",
      total: "16.000",
      awaiting_quote: false,
    };
    for (const lang of ["ar", "en"] as const) {
      expect(buildOrderMessage(order, lang)).not.toMatch(/دفع|payment|pay|كاش|cash/i);
    }
  });
});

describe("whatsappUrl", () => {
  it("encodes the text for wa.me", () => {
    expect(whatsappUrl("962790087017", "طلب 1\nسطر")).toBe(
      "https://wa.me/962790087017?text=%D8%B7%D9%84%D8%A8%201%0A%D8%B3%D8%B7%D8%B1",
    );
  });
});
