"use client";

import Link from "next/link";
import { ShoppingBag } from "lucide-react";

import { useCartUI } from "@/components/providers/cart-context";
import { EmptyState } from "@/components/feedback/empty-state";
import { ErrorState } from "@/components/feedback/error-state";
import { LoadingSkeleton } from "@/components/feedback/loading-skeleton";
import { useCart } from "@/lib/cart/use-cart";
import { formatINR, formatProductPrice } from "@/lib/cart/cart-utils";
import { Button } from "@/components/ui/button";

export function CartDrawer() {
  const { isDrawerOpen, closeDrawer } = useCartUI();
  const { items, subtotalAmount, isLoading, isError, isMutating, removeItem } = useCart();

  return (
    <div className={`fixed inset-0 z-50 ${isDrawerOpen ? "pointer-events-auto" : "pointer-events-none"}`}>
      <button
        type="button"
        aria-label="Close cart"
        onClick={closeDrawer}
        className={`absolute inset-0 bg-black/30 transition-opacity motion-slow ${isDrawerOpen ? "opacity-100" : "opacity-0"}`}
      />
      <aside
        className={`absolute right-0 top-0 flex h-dvh w-80 max-w-[88vw] flex-col bg-white p-5 pb-[calc(1.25rem+env(safe-area-inset-bottom))] pt-[calc(1.25rem+env(safe-area-inset-top))] shadow-2xl transition-transform motion-slow will-change-transform dark:bg-neutral-950 sm:p-6 ${
          isDrawerOpen ? "translate-x-0" : "translate-x-full"
        }`}
      >
        <div className="mb-6 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">Your Cart</h3>
          <Button type="button" variant="ghost" size="sm" onClick={closeDrawer}>
            Close
          </Button>
        </div>

        <div className="flex-1 space-y-3 overflow-y-auto">
          {isLoading && <LoadingSkeleton variant="list" count={3} />}
          {isError && (
            <ErrorState
              title="Cart unavailable"
              description="We could not refresh your cart. Close and retry from the cart page if this continues."
              className="p-4"
            />
          )}
          {!isLoading && !isError && items.length === 0 && (
            <EmptyState
              title="Your cart is empty"
              description="Add a product and your bag will appear here."
              icon={<ShoppingBag className="h-7 w-7" aria-hidden="true" />}
              className="border-solid p-4"
              action={
                <Button asChild className="rounded-full" onClick={closeDrawer}>
                  <Link href="/products">Shop products</Link>
                </Button>
              }
            />
          )}
          {!isLoading &&
            !isError &&
            items.map((item) => (
              <div
                key={item.id}
                className="rounded-xl border border-neutral-200 p-3 transition-[border-color,background-color,box-shadow,transform] motion-standard motion-safe:hover:-translate-y-0.5 hover:border-primary-200 hover:shadow-sm dark:border-neutral-800"
              >
                <p className="font-medium text-neutral-900 dark:text-neutral-100">{item.product.name}</p>
                <p className="text-sm text-neutral-600 dark:text-neutral-300">
                  {formatProductPrice(item.product.price)} x {item.quantity}
                </p>
                <p className="text-sm font-medium text-neutral-800 dark:text-neutral-200">
                  Line total: {formatProductPrice(item.line_total)}
                </p>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  disabled={isMutating}
                  className="mt-2 px-0 text-neutral-600 hover:bg-transparent hover:text-neutral-900 dark:text-neutral-300 dark:hover:text-neutral-100"
                  onClick={() => void removeItem(item.id)}
                >
                  Remove
                </Button>
              </div>
            ))}
        </div>

        <div className="mt-6 border-t border-neutral-200 pt-4 dark:border-neutral-800">
          <div className="mb-4 flex items-center justify-between text-sm">
            <span className="text-neutral-600 dark:text-neutral-300">Total</span>
            <span className="font-semibold text-neutral-900 dark:text-neutral-100">{formatINR(subtotalAmount)}</span>
          </div>
          <Button type="button" className="w-full" asChild disabled={items.length === 0 || isMutating}>
            <Link href="/checkout">Checkout</Link>
          </Button>
        </div>
      </aside>
    </div>
  );
}
