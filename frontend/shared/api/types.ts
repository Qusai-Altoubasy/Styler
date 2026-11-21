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

// Dashboard (/api/admin/*)
export type AdminCategory = Schemas["AdminCategoryOut"];
export type CategoryCreate = Schemas["CategoryCreate"];
export type CategoryUpdate = Schemas["CategoryUpdate"];
export type AdminProduct = Schemas["AdminProductOut"];
export type AdminProductPage = Schemas["AdminProductPage"];
export type ProductCreate = Schemas["ProductCreate"];
export type ProductUpdate = Schemas["ProductUpdate"];
export type PriceTierIn = Schemas["PriceTierIn"];
export type ColorIn = Schemas["ColorIn"];
export type UploadUrl = Schemas["UploadUrlOut"];
export type AdminSettings = Schemas["AdminSettings"];
export type SettingsUpdate = Schemas["SettingsUpdate"];
export type OrderRow = Schemas["OrderRow"];
export type OrderPage = Schemas["OrderPage"];
export type OrderStats = Schemas["OrderStats"];
export type OrderDetail = Schemas["OrderDetail"];
export type OrderUpdate = Schemas["OrderUpdate"];
export type OrderStatus = Schemas["OrderStatus"];
export type MarkFilter = Schemas["MarkFilter"];
