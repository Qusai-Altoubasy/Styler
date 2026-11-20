import type { OrderConfirmation, OrderItemOut } from "@styler/shared/api/types";
import { type Lang, pickOptional } from "@styler/shared/i18n/setup";
import { trimAmount } from "@styler/shared/utils/money";
import { GOVERNORATE_NAMES } from "@styler/shared/utils/governorates";

/** The words of the message in each language. Product details come from the order. */
const WORDS = {
  ar: {
    greeting: "مرحباً Styler، بدي أطلب:",
    orderNumber: "رقم الطلب",
    name: "الاسم",
    phone: "الهاتف",
    governorate: "المحافظة",
    address: "العنوان",
    products: "المنتجات:",
    quantity: "الكمية",
    approx: "كمية تقريبية",
    count: "العدد",
    color: "اللون",
    price: "السعر",
    quote: "عرض سعر (بانتظار التسعير)",
    delivery: "التوصيل",
    free: "مجاني",
    total: "الإجمالي",
    quoteNote: "(الإجمالي لا يشمل المنتجات التي بانتظار التسعير)",
    currency: "د.أ",
  },
  en: {
    greeting: "Hello Styler, I'd like to order:",
    orderNumber: "Order number",
    name: "Name",
    phone: "Phone",
    governorate: "Governorate",
    address: "Address",
    products: "Products:",
    quantity: "Quantity",
    approx: "Approximate quantity",
    count: "How many",
    color: "Color",
    price: "Price",
    quote: "quote (awaiting a price)",
    delivery: "Delivery",
    free: "Free",
    total: "Total",
    quoteNote: "(The total does not include products awaiting a price)",
    currency: "JOD",
  },
} as const;

/**
 * The ready-made WhatsApp message to the store, in the language the customer is
 * browsing in. Every number comes from the server's confirmation, never from the cart.
 */
export function buildOrderMessage(order: OrderConfirmation, lang: Lang): string {
  const w = WORDS[lang];
  const money = (amount: string) => `${trimAmount(amount)} ${w.currency}`;
  const lines = order.items.map((item, i) => {
    const { name, note, color } = itemText(item, lang);
    const parts = [`${i + 1}) ${name}`];
    if (item.pricing_mode === "fixed" && item.quantity !== null) {
      parts.push(`   ${w.quantity}: ${pieces(item.quantity, lang)}${note ? ` (${note})` : ""}`);
    }
    if (item.pricing_mode === "quote" && item.quantity !== null) {
      parts.push(`   ${w.approx}: ${item.quantity}`);
    }
    if (item.item_count > 1) parts.push(`   ${w.count}: ${item.item_count}`);
    if (color) parts.push(`   ${w.color}: ${color}`);
    parts.push(`   ${w.price}: ${item.line_total !== null ? money(item.line_total) : w.quote}`);
    return parts.join("\n");
  });

  const delivery = Number(order.delivery_fee) === 0 ? w.free : money(order.delivery_fee);
  return [
    w.greeting,
    `${w.orderNumber}: ${order.id}`,
    "",
    `${w.name}: ${order.customer_name}`,
    `${w.phone}: ${order.phone}`,
    `${w.governorate}: ${GOVERNORATE_NAMES[order.governorate][lang]}`,
    `${w.address}: ${order.address}`,
    "",
    w.products,
    ...lines,
    "",
    `${w.delivery}: ${delivery}`,
    `${w.total}: ${money(order.total)}`,
    ...(order.awaiting_quote ? [w.quoteNote] : []),
  ].join("\n");
}

/** Each field in the page language, falling back to the other where it is empty. */
function itemText(item: OrderItemOut, lang: Lang) {
  return {
    name: pickOptional(item, "product_name", lang) ?? "",
    note: pickOptional(item, "tier_note", lang),
    color: pickOptional(item, "color_name", lang),
  };
}

function pieces(n: number, lang: Lang): string {
  if (lang === "en") return n === 1 ? "1 piece" : `${n} pieces`;
  if (n === 1) return "قطعة واحدة";
  if (n === 2) return "قطعتان";
  if (n >= 3 && n <= 10) return `${n} قطع`;
  return `${n} قطعة`;
}

/** A wa.me link to the store's number with the message filled in. */
export function whatsappUrl(international: string, text: string): string {
  return `https://wa.me/${international}?text=${encodeURIComponent(text)}`;
}
