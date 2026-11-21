/** One page of a paged admin list: `{items, total, limit, offset}`. */
interface Page {
  items: unknown[];
  total: number;
  offset: number;
}

/** Rows per request in the dashboard's paged lists (the API allows up to 100). */
export const PAGE_SIZE = 50;

/** Where the next page starts, or undefined after the last one (TanStack's getNextPageParam). */
export function nextOffset(last: Page): number | undefined {
  const end = last.offset + last.items.length;
  return last.items.length > 0 && end < last.total ? end : undefined;
}
