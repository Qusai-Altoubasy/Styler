import createClient from "openapi-fetch";
import type { paths } from "./schema";

/** Talks to the API on the app's own domain (no CORS): `/api/*` is proxied in dev. */
export const api = createClient<paths>({ baseUrl: "" });

/** The backend's business-rule error: `{"error": {"code", "message", "details"}}`. */
export interface ApiErrorBody {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    readonly details: Record<string, unknown> = {},
    /** Seconds to wait, from `Retry-After` on a 429. */
    readonly retryAfter: number | null = null,
  ) {
    super(code);
    this.name = "ApiError";
  }
}

/**
 * Turns an openapi-fetch result into data or a thrown ApiError. FastAPI's own 422
 * body (`detail`) has no code, so it becomes `invalid_request`.
 */
export function unwrap<T>(result: { data?: T; error?: unknown; response: Response }): T {
  if (result.data !== undefined && result.response.ok) return result.data;
  const { status, headers } = result.response;
  const body = result.error as { error?: ApiErrorBody } | undefined;
  const retry = Number(headers.get("Retry-After"));
  throw new ApiError(
    status,
    body?.error?.code ?? (status === 422 ? "invalid_request" : "unexpected"),
    body?.error?.details ?? {},
    Number.isFinite(retry) && retry > 0 ? retry : null,
  );
}
