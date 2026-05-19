"use client";

import {
  queryOptions,
  useMutation,
  useQuery,
  useQueryClient,
  type QueryClient,
} from "@tanstack/react-query";

import {
  addToCart as addToCartRequest,
  cartQueryKeys,
  clearCart as clearCartRequest,
  getCart,
  removeCartItem as removeCartItemRequest,
  updateCartItem as updateCartItemRequest,
} from "@/lib/api/cart";
import type { CartProductSummary, ServerCartItem, ServerCartView } from "@/lib/api/types";

import {
  buildOptimisticAddItem,
  EMPTY_CART_VIEW,
  normalizeCartView,
  parseDecimal,
  recalculateCartRollups,
} from "./cart-utils";

export { cartQueryKeys };

export function activeCartQueryOptions(enabled: boolean) {
  return queryOptions({
    queryKey: cartQueryKeys.active(),
    queryFn: getCart,
    enabled,
    staleTime: 30_000,
  });
}

export function useActiveCartQuery(enabled: boolean) {
  return useQuery(activeCartQueryOptions(enabled));
}

function setCartCache(queryClient: QueryClient, cart: ServerCartView) {
  queryClient.setQueryData(cartQueryKeys.active(), normalizeCartView(cart));
}

type AddToCartVariables = {
  productId: number;
  quantity: number;
  product?: CartProductSummary;
};

type UpdateQuantityVariables = {
  itemId: number;
  quantity: number;
};

export function useAddToCartMutation(enabled: boolean) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ productId, quantity }: AddToCartVariables) => addToCartRequest(productId, quantity),
    onMutate: async ({ productId, quantity, product }) => {
      if (!enabled) {
        return { previousCart: undefined as ServerCartView | undefined };
      }

      await queryClient.cancelQueries({ queryKey: cartQueryKeys.active() });
      const previousCart = queryClient.getQueryData<ServerCartView>(cartQueryKeys.active());
      const currentCart = normalizeCartView(previousCart);

      if (!product) {
        return { previousCart };
      }

      const optimisticItem = buildOptimisticAddItem(currentCart, product, quantity);
      const remainingItems = currentCart.items.filter((item) => item.product.id !== productId);
      const nextItems = [...remainingItems, optimisticItem];
      const rollups = recalculateCartRollups(nextItems);

      setCartCache(queryClient, {
        ...currentCart,
        ...rollups,
      });

      return { previousCart };
    },
    onError: (_error, _variables, context) => {
      if (context?.previousCart) {
        setCartCache(queryClient, context.previousCart);
      }
    },
    onSuccess: (cart) => {
      setCartCache(queryClient, cart);
    },
  });
}

export function useUpdateCartQuantityMutation(enabled: boolean) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ itemId, quantity }: UpdateQuantityVariables) => updateCartItemRequest(itemId, quantity),
    onMutate: async ({ itemId, quantity }) => {
      if (!enabled) {
        return { previousCart: undefined as ServerCartView | undefined };
      }

      await queryClient.cancelQueries({ queryKey: cartQueryKeys.active() });
      const previousCart = queryClient.getQueryData<ServerCartView>(cartQueryKeys.active());
      const currentCart = normalizeCartView(previousCart);

      const nextItems = currentCart.items.map((item) => {
        if (item.id !== itemId) {
          return item;
        }

        const unitPrice = parseDecimal(item.product.price) || parseDecimal(item.line_total) / Math.max(item.quantity, 1);
        return {
          ...item,
          quantity,
          line_total: (unitPrice * quantity).toFixed(2),
        };
      });

      setCartCache(queryClient, {
        ...currentCart,
        ...recalculateCartRollups(nextItems),
      });

      return { previousCart };
    },
    onError: (_error, _variables, context) => {
      if (context?.previousCart) {
        setCartCache(queryClient, context.previousCart);
      }
    },
    onSuccess: (cart) => {
      setCartCache(queryClient, cart);
    },
  });
}

export function useRemoveCartItemMutation(enabled: boolean) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (itemId: number) => removeCartItemRequest(itemId),
    onMutate: async (itemId) => {
      if (!enabled) {
        return { previousCart: undefined as ServerCartView | undefined };
      }

      await queryClient.cancelQueries({ queryKey: cartQueryKeys.active() });
      const previousCart = queryClient.getQueryData<ServerCartView>(cartQueryKeys.active());
      const currentCart = normalizeCartView(previousCart);
      const nextItems = currentCart.items.filter((item) => item.id !== itemId);

      setCartCache(queryClient, {
        ...currentCart,
        ...recalculateCartRollups(nextItems),
      });

      return { previousCart };
    },
    onError: (_error, _variables, context) => {
      if (context?.previousCart) {
        setCartCache(queryClient, context.previousCart);
      }
    },
    onSuccess: (cart) => {
      setCartCache(queryClient, cart);
    },
  });
}

export function useClearCartMutation(enabled: boolean) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: clearCartRequest,
    onMutate: async () => {
      if (!enabled) {
        return { previousCart: undefined as ServerCartView | undefined };
      }

      await queryClient.cancelQueries({ queryKey: cartQueryKeys.active() });
      const previousCart = queryClient.getQueryData<ServerCartView>(cartQueryKeys.active());
      const currentCart = normalizeCartView(previousCart);

      setCartCache(queryClient, {
        ...currentCart,
        items: [],
        item_count: 0,
        subtotal: "0.00",
      });

      return { previousCart };
    },
    onError: (_error, _variables, context) => {
      if (context?.previousCart) {
        setCartCache(queryClient, context.previousCart);
      }
    },
    onSuccess: (cart) => {
      setCartCache(queryClient, cart);
    },
  });
}

export function prefetchActiveCart(queryClient: QueryClient, enabled: boolean) {
  if (!enabled) {
    queryClient.setQueryData(cartQueryKeys.active(), EMPTY_CART_VIEW);
    return Promise.resolve();
  }

  return queryClient.prefetchQuery(activeCartQueryOptions(true));
}

export function getCachedActiveCart(queryClient: QueryClient): ServerCartView {
  return normalizeCartView(queryClient.getQueryData<ServerCartView>(cartQueryKeys.active()));
}

