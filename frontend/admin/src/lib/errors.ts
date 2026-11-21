import { useCallback } from "react";
import { useTranslation } from "react-i18next";
import { ApiError } from "@styler/shared/api/client";
import { ImageReadError, ImageTooLargeError } from "./image";
import { UploadError } from "./upload";

/** Error codes with their own sentence in `common:errors`; anything else is generic. */
const KNOWN = new Set([
  "invalid_password",
  "password_not_set",
  "wrong_current_password",
  "category_name_taken",
  "category_has_products",
  "category_not_found",
  "product_not_found",
  "order_not_found",
  "order_item_not_found",
  "item_price_fixed",
  "duplicate_price_tier",
  "price_tier_not_found",
  "color_not_found",
  "image_not_uploaded",
  "image_in_use",
  "invalid_image_key",
  "storage_misconfigured",
  "invalid_request",
]);

/** Turns any thrown error into one sentence the manager can act on, in the page language. */
export function useErrorText() {
  const { t } = useTranslation();
  return useCallback(
    (error: unknown): string => {
      if (error instanceof ImageReadError) return t("errors.image_unreadable");
      if (error instanceof ImageTooLargeError) return t("errors.image_too_large");
      if (error instanceof UploadError) return t("errors.upload_failed");
      if (error instanceof ApiError) {
        if (error.status === 429) {
          const minutes = Math.max(1, Math.ceil((error.retryAfter ?? 60) / 60));
          return t("errors.too_many", { count: minutes });
        }
        if (error.code === "category_name_taken") {
          const field = error.details.field === "name_en" ? "name_en" : "name_ar";
          return t(`errors.category_name_taken_${field}`);
        }
        if (KNOWN.has(error.code)) return t(`errors.${error.code}`);
        if (error.status >= 500) return t("errors.server");
        return t("errors.unexpected");
      }
      if (isNetworkError(error)) return t("errors.offline");
      return t("errors.unexpected");
    },
    [t],
  );
}

/** "Log in first": the session ended (logged out elsewhere, expired, password changed). */
export function isSessionEnded(error: unknown): boolean {
  return error instanceof ApiError && error.status === 401 && error.code === "not_authenticated";
}

export function isNotFound(error: unknown): boolean {
  return error instanceof ApiError && error.status === 404;
}

/**
 * fetch() itself failed (no connection, server unreachable). Browsers throw a TypeError
 * with their own wording; other TypeErrors are bugs and must not read as "offline".
 */
export function isNetworkError(error: unknown): boolean {
  if (!(error instanceof TypeError)) return false;
  return (
    !navigator.onLine || /failed to fetch|load failed|networkerror|network/i.test(error.message)
  );
}

/** Worth trying again: no connection or a server error, never a refused request. */
export function isRetryable(error: unknown): boolean {
  if (error instanceof ApiError) return error.status >= 500;
  return isNetworkError(error);
}
