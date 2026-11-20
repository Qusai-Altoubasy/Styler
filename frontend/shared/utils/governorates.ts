import type { Governorate } from "../api/types";

/** Display names of the 12 governorates; the list and zones come from the API settings. */
export const GOVERNORATE_NAMES: Record<Governorate, { ar: string; en: string }> = {
  amman: { ar: "عمّان", en: "Amman" },
  zarqa: { ar: "الزرقاء", en: "Zarqa" },
  irbid: { ar: "إربد", en: "Irbid" },
  balqa: { ar: "البلقاء", en: "Balqa" },
  madaba: { ar: "مادبا", en: "Madaba" },
  mafraq: { ar: "المفرق", en: "Mafraq" },
  jerash: { ar: "جرش", en: "Jerash" },
  ajloun: { ar: "عجلون", en: "Ajloun" },
  karak: { ar: "الكرك", en: "Karak" },
  tafilah: { ar: "الطفيلة", en: "Tafilah" },
  maan: { ar: "معان", en: "Ma'an" },
  aqaba: { ar: "العقبة", en: "Aqaba" },
};
