import type { CartProductSummary, ServerCart, ServerCartItem, ServerCartView } from "@/lib/api/types";

/** Minimal product input used by legacy UI (home featured cards, wishlist). */
export type CartProductInput = {
  id: number;
  name: string;
  price: string;
};


export const EMPTY_CART_VIEW: ServerCartView = {
  id: 0,
  user: "",
  is_active: false,
  created_at: "",
  updated_at: "",
  items: [],
  item_count: 0,
  subtotal: "0.00",
};

const inrFormatter = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 2,
});

export function parseDecimal(value: string | number | null | undefined): number {
  if (typeof value === "number") {
    return Number.isFinite(value) ? value : 0;
  }
  if (value == null) {
    return 0;
  }
  const sanitized = String(value).replace(/[^0-9.]/g, "");
  if ((sanitized.match(/\./g) || []).length > 1) {
    return 0;
  }
  const parsed = Number(sanitized);
  return Number.isFinite(parsed) ? parsed : 0;
}

export function formatINR(value: number): string {
  return inrFormatter.format(value);
}

export function formatProductPrice(price: string): string {
  const amount = parseDecimal(price);
  return formatINR(amount);
}

export function normalizeCartView(data: ServerCartView | undefined): ServerCartView {
  if (!data) {
    return EMPTY_CART_VIEW;
  }

  return {
    ...data,
    items: data.items ?? [],
    item_count: data.item_count ?? 0,
    subtotal: data.subtotal ?? "0.00",
  };
}

export function getCartHeader(cart: ServerCartView): ServerCart | null {
  if (!cart.id) {
    return null;
  }

  return {
    id: cart.id,
    user: cart.user,
    is_active: cart.is_active,
    created_at: cart.created_at,
    updated_at: cart.updated_at,
  };
}

export function getSubtotalAmount(cart: ServerCartView): number {
  return parseDecimal(cart.subtotal);
}

export function findCartItemByProductId(items: ServerCartItem[], productId: number): ServerCartItem | undefined {
  return items.find((item) => item.product.id === productId);
}

export function buildOptimisticAddItem(
  cart: ServerCartView,
  product: CartProductSummary,
  quantity: number,
): ServerCartItem {
  const existing = findCartItemByProductId(cart.items, product.id);
  const unitPrice = parseDecimal(product.price);
  const nextQuantity = (existing?.quantity ?? 0) + quantity;
  const lineTotal = (unitPrice * nextQuantity).toFixed(2);

  if (existing) {
    return {
      ...existing,
      quantity: nextQuantity,
      line_total: lineTotal,
      product,
    };
  }

  return {
    id: Date.now() * -1,
    cart: cart.id,
    product,
    quantity,
    line_total: (unitPrice * quantity).toFixed(2),
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };
}

export function recalculateCartRollups(items: ServerCartItem[]): Pick<ServerCartView, "items" | "item_count" | "subtotal"> {
  const item_count = items.reduce((sum, item) => sum + item.quantity, 0);
  const subtotalValue = items.reduce((sum, item) => sum + parseDecimal(item.line_total), 0);

  return {
    items,
    item_count,
    subtotal: subtotalValue.toFixed(2),
  };
}

export function isCartProductInput(value: number | CartProductInput): value is CartProductInput {
  return typeof value === "object" && value !== null && "id" in value;
}
