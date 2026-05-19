"use client";

import { createContext, useCallback, useContext, useMemo, useState } from "react";

type CartUIContextValue = {
  isDrawerOpen: boolean;
  openDrawer: () => void;
  closeDrawer: () => void;
  toggleDrawer: () => void;
};

const CartUIContext = createContext<CartUIContextValue | undefined>(undefined);

/**
 * UI-only cart shell state (drawer open/close).
 * Cart data lives in React Query — see `useCart()` from `@/lib/cart/use-cart`.
 */
export function CartProvider({ children }: { children: React.ReactNode }) {
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  const openDrawer = useCallback(() => {
    setIsDrawerOpen(true);
  }, []);

  const closeDrawer = useCallback(() => {
    setIsDrawerOpen(false);
  }, []);

  const toggleDrawer = useCallback(() => {
    setIsDrawerOpen((open) => !open);
  }, []);

  const value = useMemo(
    () => ({
      isDrawerOpen,
      openDrawer,
      closeDrawer,
      toggleDrawer,
    }),
    [closeDrawer, isDrawerOpen, openDrawer, toggleDrawer],
  );

  return <CartUIContext.Provider value={value}>{children}</CartUIContext.Provider>;
}

export function useCartUI() {
  const context = useContext(CartUIContext);
  if (!context) {
    throw new Error("useCartUI must be used within a CartProvider");
  }
  return context;
}

/** @deprecated Use `useCart` from `@/lib/cart/use-cart` for cart data. */
export { useCart } from "@/lib/cart/use-cart";

/** @deprecated Use `CartProductInput` from `@/lib/cart/cart-utils`. */
export type { CartProductInput as CartProduct } from "@/lib/cart/cart-utils";

