import { apiClient } from "@/lib/api/client";
import type { Cart, CartItem, ServerCart, ServerCartItem, ServerCartView } from "@/lib/api/types";

/** React Query key factory for the server cart. */
export const cartQueryKeys = {
  all: ["server-cart"] as const,
  active: () => [...cartQueryKeys.all, "active"] as const,
};

/** Result shape returned by cart mutations (ready for `queryClient.setQueryData`). */
export type ServerCartMutationResult = ServerCartView;

const ACTIVE_CART_URL = "/api/v1/orders/carts/active/";
const CART_ITEMS_URL = "/api/v1/orders/cart-items/";

function mapActiveCartResponse(data: ServerCartView): ServerCartView {
  return {
    ...data,
    items: data.items ?? [],
    item_count: data.item_count ?? 0,
    subtotal: data.subtotal ?? "0.00",
  };
}

/**
 * Ensures the authenticated user has exactly one active cart row.
 * Uses `GET /carts/active/` which creates an empty active cart when missing.
 */
export async function ensureActiveCart(): Promise<ServerCart> {
  const view = await getCart();
  return {
    id: view.id,
    user: view.user,
    is_active: view.is_active,
    created_at: view.created_at,
    updated_at: view.updated_at,
  };
}

/**
 * Loads the active cart with nested product summaries in a single request.
 */
export async function getCart(): Promise<ServerCartView> {
  const { data } = await apiClient.get<ServerCartView>(ACTIVE_CART_URL);
  return mapActiveCartResponse(data);
}

/**
 * Adds quantity for a product on the active cart.
 * Backend merges into an existing line (unique cart + product constraint).
 */
export async function addToCart(productId: number, quantity = 1): Promise<ServerCartMutationResult> {
  if (quantity < 1) {
    throw new Error("Quantity must be at least 1.");
  }

  const cart = await ensureActiveCart();
  await apiClient.post<ServerCartItem>(CART_ITEMS_URL, {
    cart: cart.id,
    product: productId,
    quantity,
  });

  return getCart();
}

/**
 * Sets line quantity. Pass a lower quantity to decrease units (minimum 1).
 */
export async function updateCartItem(itemId: number, quantity: number): Promise<ServerCartMutationResult> {
  if (quantity < 1) {
    throw new Error("Quantity must be at least 1. Use removeCartItem() to delete a line.");
  }

  await apiClient.patch<ServerCartItem>(`${CART_ITEMS_URL}${itemId}/`, { quantity });
  return getCart();
}

/**
 * Removes a single cart line by id.
 */
export async function removeCartItem(itemId: number): Promise<ServerCartMutationResult> {
  await apiClient.delete(`${CART_ITEMS_URL}${itemId}/`);
  return getCart();
}

/**
 * Deletes all items from the active cart (cart row remains active).
 */
export async function clearCart(): Promise<ServerCartMutationResult> {
  await apiClient.delete(`${ACTIVE_CART_URL}clear/`);
  return getCart();
}

// ---------------------------------------------------------------------------
// Legacy adapter — keeps existing `/cart` page working until UI migration.
// ---------------------------------------------------------------------------

export type LegacyCartItemWithProduct = CartItem & {
  product_details?: ServerCartItem["product"];
};

export type LegacyCartView = {
  cart: Cart | null;
  items: LegacyCartItemWithProduct[];
};

/**
 * @deprecated Use `getCart()` and `ServerCartView` instead.
 * Maps the server cart into the legacy `{ cart, items, product_details }` shape.
 */
export async function fetchCart(): Promise<LegacyCartView> {
  const view = await getCart();

  return {
    cart: {
      id: view.id,
      user: view.user,
      is_active: view.is_active,
      created_at: view.created_at,
      updated_at: view.updated_at,
    },
    items: view.items.map((item) => ({
      id: item.id,
      cart: item.cart,
      product: item.product.id,
      quantity: item.quantity,
      created_at: item.created_at,
      updated_at: item.updated_at,
      product_details: item.product,
    })),
  };
}
