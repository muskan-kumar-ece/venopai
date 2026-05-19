"use client";

import { useCallback, useMemo } from "react";

import { useAuthStore } from "@/lib/stores/auth-store";
import type { CartProductSummary, ServerCart, ServerCartItem, ServerCartView } from "@/lib/api/types";

import {
  useActiveCartQuery,
  useAddToCartMutation,
  useClearCartMutation,
  useRemoveCartItemMutation,
  useUpdateCartQuantityMutation,
} from "./cart-query";
import {
  type CartProductInput,
  EMPTY_CART_VIEW,
  getCartHeader,
  getSubtotalAmount,
  isCartProductInput,
  normalizeCartView,
} from "./cart-utils";

export type UseCartResult = {
  /** Full active cart payload from the server (React Query cache). */
  cartView: ServerCartView;
  /** Cart header metadata, or `null` when unauthenticated / empty. */
  cart: ServerCart | null;
  /** Quantity-based server line items. */
  items: ServerCartItem[];
  subtotal: string;
  subtotalAmount: number;
  itemCount: number;
  isLoading: boolean;
  isFetching: boolean;
  isError: boolean;
  error: Error | null;
  isAuthenticated: boolean;
  isMutating: boolean;
  addToCart: {
    (productId: number, quantity?: number, product?: CartProductSummary): Promise<ServerCartView>;
    (product: CartProductInput, quantity?: number): Promise<ServerCartView>;
  };
  updateQuantity: (itemId: number, quantity: number) => Promise<ServerCartView>;
  removeItem: (itemId: number) => Promise<ServerCartView>;
  clearCart: () => Promise<ServerCartView>;
  refetch: () => Promise<unknown>;
  /** @deprecated Use `itemCount`. */
  totalItems: number;
  /** @deprecated Accepts `productId` or legacy `{ id, name, price }` product cards. */
  addToCartLegacy: (productOrId: number | CartProductInput, quantity?: number) => Promise<ServerCartView>;
};

/**
 * Server-backed cart domain hook. React Query owns cart data; this hook exposes
 * mutations, rollups, and thin legacy adapters for pages not yet migrated.
 */
export function useCart(): UseCartResult {
  const accessToken = useAuthStore((state) => state.accessToken);
  const isAuthenticated = Boolean(accessToken);

  const cartQuery = useActiveCartQuery(isAuthenticated);
  const addMutation = useAddToCartMutation(isAuthenticated);
  const updateMutation = useUpdateCartQuantityMutation(isAuthenticated);
  const removeMutation = useRemoveCartItemMutation(isAuthenticated);
  const clearMutation = useClearCartMutation(isAuthenticated);

  const cartView = useMemo(() => {
    if (!isAuthenticated) {
      return EMPTY_CART_VIEW;
    }
    return normalizeCartView(cartQuery.data);
  }, [cartQuery.data, isAuthenticated]);

  const items = cartView.items;
  const itemCount = cartView.item_count;
  const subtotal = cartView.subtotal;
  const subtotalAmount = getSubtotalAmount(cartView);
  const cart = getCartHeader(cartView);

  const addToCartById = useCallback(
    async (productId: number, quantity = 1, product?: CartProductSummary) => {
      return addMutation.mutateAsync({ productId, quantity, product });
    },
    [addMutation],
  );

  const updateQuantity = useCallback(
    async (itemId: number, quantity: number) => {
      return updateMutation.mutateAsync({ itemId, quantity });
    },
    [updateMutation],
  );

  const removeItem = useCallback(
    async (itemId: number) => {
      return removeMutation.mutateAsync(itemId);
    },
    [removeMutation],
  );

  const clearCart = useCallback(async () => {
    return clearMutation.mutateAsync();
  }, [clearMutation]);

  const addToCartLegacy = useCallback(
    async (productOrId: number | CartProductInput, quantity = 1) => {
      if (isCartProductInput(productOrId)) {
        const summary: CartProductSummary = {
          id: productOrId.id,
          name: productOrId.name,
          slug: "",
          sku: "",
          price: productOrId.price,
          stock_quantity: 0,
          is_active: true,
          is_refurbished: false,
          condition_grade: "",
          category_name: "",
          image_url: null,
          image_url_card: null,
        };
        return addToCartById(productOrId.id, quantity, summary);
      }
      return addToCartById(productOrId, quantity);
    },
    [addToCartById],
  );

  const addToCart = useCallback(
    async (productOrId: number | CartProductInput, quantity = 1, product?: CartProductSummary) => {
      if (isCartProductInput(productOrId)) {
        return addToCartLegacy(productOrId, quantity);
      }
      return addToCartById(productOrId, quantity, product);
    },
    [addToCartById, addToCartLegacy],
  ) as UseCartResult["addToCart"];

  const isMutating =
    addMutation.isPending ||
    updateMutation.isPending ||
    removeMutation.isPending ||
    clearMutation.isPending;

  return {
    cartView,
    cart,
    items,
    subtotal,
    subtotalAmount,
    itemCount,
    isLoading: isAuthenticated && cartQuery.isLoading,
    isFetching: isAuthenticated && cartQuery.isFetching,
    isError: isAuthenticated && cartQuery.isError,
    error: cartQuery.error ?? null,
    isAuthenticated,
    isMutating,
    addToCart,
    updateQuantity,
    removeItem,
    clearCart,
    refetch: cartQuery.refetch,
    totalItems: itemCount,
    addToCartLegacy,
  };
}
