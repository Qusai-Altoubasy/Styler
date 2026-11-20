import type { components } from "./schema";

type Schemas = components["schemas"];

export type CategoryCard = Schemas["CategoryCard"];
export type ProductCard = Schemas["ProductCard"];
export type ProductDetail = Schemas["ProductDetail"];
export type PriceTier = Schemas["PriceTierOut"];
export type ProductColor = Schemas["ColorOut"];
export type PublicSettings = Schemas["PublicSettings"];
export type OrderCreate = Schemas["OrderCreate"];
export type OrderItemIn = Schemas["OrderItemIn"];
export type OrderConfirmation = Schemas["OrderConfirmation"];
export type OrderItemOut = Schemas["OrderItemOut"];
export type Governorate = Schemas["Governorate"];
export type PricingMode = Schemas["PricingMode"];
export type ProductSort = Schemas["ProductSort"];
export type BrandColor = Schemas["BrandColor"];
export type Language = Schemas["Language"];
