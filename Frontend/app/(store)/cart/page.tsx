"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect } from "react";
import {
  ArrowRight,
  BadgeCheck,
  ChevronLeft,
  Minus,
  PackageCheck,
  Plus,
  RotateCcw,
  ShieldCheck,
  ShoppingBag,
  Trash2,
  Truck,
} from "lucide-react";

import { ErrorState } from "@/components/feedback/error-state";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ProductCardSkeleton } from "@/components/products/product-card";
import { formatINR, formatProductPrice } from "@/lib/cart/cart-utils";
import { useCart } from "@/lib/cart/use-cart";
import { trackEvent } from "@/lib/observability";

const cartImages = [
  "https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=600&q=80",
  "https://images.unsplash.com/photo-1606220588913-b3aacb4d2f46?auto=format&fit=crop&w=600&q=80",
  "https://images.unsplash.com/photo-1622560480605-d83c853bc5c3?auto=format&fit=crop&w=600&q=80",
  "https://images.unsplash.com/photo-1507473885765-e6ed057f782c?auto=format&fit=crop&w=600&q=80",
];

export default function CartPage() {
  const {
    items,
    itemCount,
    subtotalAmount,
    isLoading,
    isError,
    isFetching,
    isMutating,
    updateQuantity,
    removeItem,
    clearCart,
    refetch,
  } = useCart();

  useEffect(() => {
    return () => {
      if (items.length) {
        trackEvent("cart_abandoned", { item_count: items.length });
      }
    };
  }, [items.length]);

  const deliveryFee = subtotalAmount > 0 && subtotalAmount < 999 ? 99 : 0;
  const savings = subtotalAmount > 0 ? Math.round(subtotalAmount * 0.08) : 0;
  const estimatedTotal = subtotalAmount + deliveryFee;

  if (isError) {
    return (
      <ErrorState
        title="Unable to load cart"
        description="Your cart did not refresh cleanly. Retry to reconnect your bag before checkout."
        onRetry={() => void refetch()}
        isRetrying={isFetching}
      />
    );
  }

  if (isLoading) {
    return (
      <section className="space-y-6">
        <div className="h-40 rounded-3xl bg-surface-100 dark:bg-surface-900" />
        <div className="grid gap-4 lg:grid-cols-[1fr_360px]">
          <div className="space-y-4">
            {Array.from({ length: 3 }).map((_, index) => (
              <ProductCardSkeleton key={index} />
            ))}
          </div>
          <div className="h-80 rounded-3xl bg-surface-100 dark:bg-surface-900" />
        </div>
      </section>
    );
  }

  if (items.length === 0) {
    return (
      <section className="mx-auto max-w-3xl py-12 text-center">
        <div className="rounded-[2rem] border border-surface-200 bg-white p-8 shadow-sm dark:border-surface-800 dark:bg-surface-900 sm:p-10">
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-3xl bg-primary-50 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300">
            <ShoppingBag className="h-8 w-8" aria-hidden="true" />
          </div>
          <h1 className="mt-6 text-3xl font-black tracking-tight text-surface-950 dark:text-white">Your cart is waiting.</h1>
          <p className="mx-auto mt-3 max-w-xl text-sm leading-6 text-surface-600 dark:text-surface-300">
            Discover premium picks, add your favorites, and come back here for a secure checkout experience.
          </p>
          <div className="mt-7 flex flex-col justify-center gap-3 sm:flex-row">
            <Button asChild size="lg" className="rounded-full">
              <Link href="/products">
                Continue shopping <ArrowRight className="ml-2 h-4 w-4" aria-hidden="true" />
              </Link>
            </Button>
            <Button asChild size="lg" variant="outline" className="rounded-full">
              <Link href="/">Explore featured</Link>
            </Button>
          </div>
          <div className="mt-8 grid gap-3 text-left sm:grid-cols-3">
            {[
              { icon: ShieldCheck, text: "Secure checkout" },
              { icon: Truck, text: "Reliable delivery" },
              { icon: RotateCcw, text: "Easy returns" },
            ].map((item) => {
              const Icon = item.icon;
              return (
                <div key={item.text} className="rounded-2xl bg-surface-50 p-4 text-sm font-semibold text-surface-700 dark:bg-surface-800 dark:text-surface-200">
                  <Icon className="mb-2 h-5 w-5 text-primary-600" aria-hidden="true" />
                  {item.text}
                </div>
              );
            })}
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="space-y-6 pb-[calc(7rem+env(safe-area-inset-bottom))] lg:pb-0">
      <div className="rounded-3xl border border-surface-200 bg-gradient-to-br from-white via-primary-50 to-surface-50 p-5 shadow-sm dark:border-surface-800 dark:from-surface-900 dark:via-surface-900 dark:to-neutral-950 sm:p-6">
        <Link href="/products" className="inline-flex items-center gap-2 text-sm font-semibold text-primary-700 hover:text-primary-800 dark:text-primary-300">
          <ChevronLeft className="h-4 w-4" aria-hidden="true" />
          Continue shopping
        </Link>
        <div className="mt-4 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-wide text-primary-700 dark:text-primary-300">Shopping cart</p>
            <h1 className="mt-2 text-3xl font-black tracking-tight text-surface-950 dark:text-white sm:text-4xl">
              Review your bag before checkout.
            </h1>
            <p className="mt-2 text-sm text-surface-600 dark:text-surface-300">
              {itemCount} {itemCount === 1 ? "item" : "items"} ready for secure checkout.
            </p>
          </div>
          <Button type="button" variant="ghost" className="self-start rounded-full" disabled={isMutating} onClick={() => void clearCart()}>
            Clear cart
          </Button>
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1fr_380px]">
        <div className="space-y-4">
          {items.map((item, index) => {
            const product = item.product;
            const image = product.image_url_card ?? product.image_url ?? cartImages[product.id % cartImages.length];
            const nextDecrement = item.quantity - 1;
            return (
              <Card key={item.id} className="overflow-hidden rounded-3xl border-surface-200 bg-white shadow-sm transition-all duration-300 hover:border-primary-200 hover:shadow-lg hover:shadow-primary-900/10 dark:border-surface-800 dark:bg-surface-900">
                <CardContent className="grid gap-4 p-4 sm:grid-cols-[120px_1fr] md:grid-cols-[132px_1fr] sm:p-5">
                  <Link
                    href={`/products/${product.slug}`}
                    className="relative aspect-square overflow-hidden rounded-2xl bg-surface-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2 dark:bg-surface-800 sm:aspect-[4/5]"
                  >
                    <Image
                      src={image}
                      alt={product.name}
                      fill
                      sizes="132px"
                      className="object-cover transition-transform duration-500 hover:scale-105"
                      priority={index === 0}
                    />
                  </Link>

                  <div className="grid gap-4">
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                      <div>
                        <p className="text-xs font-semibold uppercase tracking-wide text-primary-700 dark:text-primary-300">
                          {product.category_name || "Premium pick"}
                        </p>
                        <h2 className="mt-1 text-lg font-bold leading-snug text-surface-950 dark:text-white">
                          <Link href={`/products/${product.slug}`} className="hover:text-primary-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2 dark:hover:text-primary-300">
                            {product.name}
                          </Link>
                        </h2>
                        <p className="mt-2 text-xs font-medium text-surface-500 dark:text-surface-400">SKU: {product.sku}</p>
                      </div>
                      <div className="text-left sm:text-right">
                        <p className="text-lg font-black text-surface-950 dark:text-white">{formatProductPrice(item.line_total)}</p>
                        <p className="text-xs text-surface-500 dark:text-surface-400">{formatProductPrice(product.price)} each</p>
                      </div>
                    </div>

                    <div className="grid gap-3 md:grid-cols-[auto_1fr_auto] md:items-center">
                      <div className="inline-flex h-11 w-fit items-center rounded-full border border-surface-300 bg-white p-1 dark:border-surface-700 dark:bg-surface-950">
                        <button
                          type="button"
                          aria-label={`Decrease quantity for ${product.name}`}
                          disabled={isMutating}
                          onClick={() => {
                            if (nextDecrement < 1) {
                              void removeItem(item.id);
                              return;
                            }
                            void updateQuantity(item.id, nextDecrement);
                          }}
                          className="flex h-9 w-9 items-center justify-center rounded-full text-surface-700 transition-colors hover:bg-surface-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 disabled:opacity-50 dark:text-surface-200 dark:hover:bg-surface-800"
                        >
                          <Minus className="h-4 w-4" aria-hidden="true" />
                        </button>
                        <span className="w-10 text-center text-sm font-bold text-surface-950 dark:text-white" aria-live="polite">
                          {item.quantity}
                        </span>
                        <button
                          type="button"
                          aria-label={`Increase quantity for ${product.name}`}
                          disabled={isMutating}
                          onClick={() => void updateQuantity(item.id, item.quantity + 1)}
                          className="flex h-9 w-9 items-center justify-center rounded-full text-surface-700 transition-colors hover:bg-surface-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 disabled:opacity-50 dark:text-surface-200 dark:hover:bg-surface-800"
                        >
                          <Plus className="h-4 w-4" aria-hidden="true" />
                        </button>
                      </div>

                      <div className="flex flex-wrap gap-2 text-xs font-semibold text-surface-500 dark:text-surface-400">
                        <span className="inline-flex items-center gap-1.5 rounded-full bg-success-50 px-2.5 py-1 text-success-700 dark:bg-success-900/30 dark:text-success-300">
                          <PackageCheck className="h-3.5 w-3.5" aria-hidden="true" />
                          In stock
                        </span>
                        <span className="inline-flex items-center gap-1.5 rounded-full bg-primary-50 px-2.5 py-1 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300">
                          <Truck className="h-3.5 w-3.5" aria-hidden="true" />
                          Delivery eligible
                        </span>
                      </div>

                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        disabled={isMutating}
                        className="w-fit rounded-full text-surface-600 hover:text-error-700 dark:text-surface-300 dark:hover:text-error-300"
                        iconLeft={<Trash2 className="h-4 w-4" />}
                        onClick={() => void removeItem(item.id)}
                      >
                        Remove
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>

        <aside className="xl:sticky xl:top-36 xl:self-start">
          <Card className="rounded-3xl border-surface-200 bg-white shadow-sm dark:border-surface-800 dark:bg-surface-900">
            <CardContent className="space-y-5 p-5">
              <div>
                <h2 className="text-xl font-black text-surface-950 dark:text-white">Order summary</h2>
                <p className="mt-1 text-sm text-surface-500 dark:text-surface-400">Clear totals before checkout.</p>
              </div>

              <div className="space-y-3 border-y border-surface-200 py-4 text-sm dark:border-surface-800">
                <div className="flex items-center justify-between">
                  <span className="text-surface-600 dark:text-surface-300">Subtotal</span>
                  <span className="font-bold text-surface-950 dark:text-white">{formatINR(subtotalAmount)}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-surface-600 dark:text-surface-300">Estimated delivery</span>
                  <span className="font-bold text-success-700 dark:text-success-300">
                    {deliveryFee ? formatINR(deliveryFee) : "Free"}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-surface-600 dark:text-surface-300">Estimated savings</span>
                  <span className="font-bold text-success-700 dark:text-success-300">{formatINR(savings)}</span>
                </div>
              </div>

              <div className="flex items-end justify-between">
                <span className="text-sm font-semibold text-surface-600 dark:text-surface-300">Estimated total</span>
                <span className="text-2xl font-black text-surface-950 dark:text-white">{formatINR(estimatedTotal)}</span>
              </div>

              <Button asChild size="lg" className="w-full rounded-full" disabled={isMutating}>
                <Link href="/checkout">
                  Proceed to checkout <ArrowRight className="ml-2 h-4 w-4" aria-hidden="true" />
                </Link>
              </Button>

              <div className="grid gap-3 rounded-2xl bg-surface-50 p-4 text-sm dark:bg-surface-800">
                <div className="flex items-center gap-2 font-bold text-surface-950 dark:text-white">
                  <ShieldCheck className="h-4 w-4 text-success-600" aria-hidden="true" />
                  Secure checkout
                </div>
                <p className="text-xs leading-5 text-surface-500 dark:text-surface-400">
                  Payment and address details are handled in the protected checkout flow.
                </p>
              </div>

              <div className="grid gap-2 text-xs font-medium text-surface-500 dark:text-surface-400">
                <span className="inline-flex items-center gap-2">
                  <BadgeCheck className="h-4 w-4 text-primary-600" aria-hidden="true" />
                  Quality checked catalog
                </span>
                <span className="inline-flex items-center gap-2">
                  <RotateCcw className="h-4 w-4 text-primary-600" aria-hidden="true" />
                  Return assurance available
                </span>
              </div>
            </CardContent>
          </Card>
        </aside>
      </div>

      <div className="fixed inset-x-0 bottom-0 z-40 border-t border-surface-200 bg-white/95 p-3 pb-[calc(0.75rem+env(safe-area-inset-bottom))] shadow-2xl backdrop-blur dark:border-surface-800 dark:bg-neutral-950/95 xl:hidden">
        <div className="mx-auto flex max-w-[1280px] items-center gap-3">
          <div className="min-w-0 flex-1">
            <p className="text-xs font-semibold text-surface-500 dark:text-surface-400">Estimated total</p>
            <p className="text-lg font-black text-surface-950 dark:text-white">{formatINR(estimatedTotal)}</p>
          </div>
          <Button asChild className="rounded-full" disabled={isMutating}>
            <Link href="/checkout">Checkout</Link>
          </Button>
        </div>
      </div>
    </section>
  );
}
