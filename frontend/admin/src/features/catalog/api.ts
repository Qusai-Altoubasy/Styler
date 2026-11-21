import {
  keepPreviousData,
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { api, unwrap, unwrapEmpty } from "@styler/shared/api/client";
import { nextOffset, PAGE_SIZE } from "../../lib/paging";
import { isNotFound } from "../../lib/errors";
import type {
  CategoryCreate,
  CategoryUpdate,
  ProductCreate,
  ProductUpdate,
} from "@styler/shared/api/types";

export function useCategories() {
  return useQuery({
    queryKey: ["categories"],
    queryFn: async () => unwrap(await api.GET("/api/admin/categories")),
  });
}

export function useSaveCategory(categoryId: number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: CategoryCreate | CategoryUpdate) =>
      categoryId === null
        ? unwrap(await api.POST("/api/admin/categories", { body: body as CategoryCreate }))
        : unwrap(
            await api.PATCH("/api/admin/categories/{category_id}", {
              params: { path: { category_id: categoryId } },
              body,
            }),
          ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["categories"] }),
  });
}

/** Refused with 409 `category_has_products` while any product (hidden too) is in it. */
export function useDeleteCategory(categoryId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () =>
      unwrapEmpty(
        await api.DELETE("/api/admin/categories/{category_id}", {
          params: { path: { category_id: categoryId } },
        }),
      ),
    // Not awaited: the page leaves right away instead of showing "not found" first.
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["categories"] });
    },
  });
}

export interface ProductFilters {
  q: string;
  categoryId: number | null;
}

/** Every product, hidden ones too, newest first, a page at a time. */
export function useProducts(filters: ProductFilters) {
  return useInfiniteQuery({
    queryKey: ["products", filters],
    queryFn: async ({ pageParam }) =>
      unwrap(
        await api.GET("/api/admin/products", {
          params: {
            query: {
              q: filters.q.trim() || undefined,
              category_id: filters.categoryId ?? undefined,
              limit: PAGE_SIZE,
              offset: pageParam,
            },
          },
        }),
      ),
    initialPageParam: 0,
    getNextPageParam: nextOffset,
    placeholderData: keepPreviousData,
  });
}

/**
 * One product for its edit page, fetched fresh each time the page opens (never from a
 * cached copy): the form sends every field, so a stale copy would undo a change made
 * since, like hiding the product from the list. Null when it no longer exists.
 */
export function useProduct(productId: number | null) {
  return useQuery({
    queryKey: ["product", productId],
    enabled: productId !== null,
    gcTime: 0,
    queryFn: async () => {
      try {
        return unwrap(
          await api.GET("/api/admin/products/{product_id}", {
            params: { path: { product_id: productId ?? 0 } },
          }),
        );
      } catch (error) {
        if (isNotFound(error)) return null;
        throw error;
      }
    },
  });
}

function useAfterProductChange() {
  const queryClient = useQueryClient();
  return () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: ["products"] }),
      queryClient.invalidateQueries({ queryKey: ["product"] }),
      // Product counts on the category cards.
      queryClient.invalidateQueries({ queryKey: ["categories"] }),
    ]);
}

export function useCreateProduct() {
  const after = useAfterProductChange();
  return useMutation({
    mutationFn: async (body: ProductCreate) =>
      unwrap(await api.POST("/api/admin/products", { body })),
    onSuccess: after,
  });
}

export function useUpdateProduct() {
  const after = useAfterProductChange();
  return useMutation({
    mutationFn: async ({ id, body }: { id: number; body: ProductUpdate }) =>
      unwrap(
        await api.PATCH("/api/admin/products/{product_id}", {
          params: { path: { product_id: id } },
          body,
        }),
      ),
    onSuccess: after,
  });
}

export function useDeleteProduct() {
  const after = useAfterProductChange();
  return useMutation({
    mutationFn: async (id: number) =>
      unwrapEmpty(
        await api.DELETE("/api/admin/products/{product_id}", {
          params: { path: { product_id: id } },
        }),
      ),
    onSuccess: () => {
      void after();
    },
  });
}
