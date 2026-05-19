"use client";

import Image from "next/image";
import Link from "next/link";
import { BadgeCheck, Heart, PackageCheck, ShoppingCart, Star, Truck } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { formatINR, parseDecimal } from "@/lib/cart/cart-utils";
import { cn } from "@/lib/utils";

export type ProductCardProduct = {
  id: number;
  name: string;
  price: string;
  slug?: string;
  description?: string;
  category_name?: string;
  stock_quantity?: number;
  average_rating?: number;
  reviews_count?: number;
  condition_grade?: string;
  is_refurbished?: boolean;
  image_url?: string | null;
  image_url_card?: string | null;
  image?: string;
  compareAtPrice?: string;
  badge?: string;
};

type ProductCardProps = {
  product: ProductCardProduct;
  href?: string;
  imageSrc?: string;
  priority?: boolean;
  className?: string;
  actionLabel?: string;
  onAddToCart?: () => void;
  isAdding?: boolean;
  showWishlist?: boolean;
  onWishlist?: () => void;
};

const fallbackImages = [
  "https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=900&q=80",
  "https://images.unsplash.com/photo-1606220588913-b3aacb4d2f46?auto=format&fit=crop&w=900&q=80",
  "https://images.unsplash.com/photo-1622560480605-d83c853bc5c3?auto=format&fit=crop&w=900&q=80",
  "https://images.unsplash.com/photo-1507473885765-e6ed057f782c?auto=format&fit=crop&w=900&q=80",
];

function getProductImage(product: ProductCardProduct, imageSrc?: string) {
  return imageSrc ?? product.image_url_card ?? product.image_url ?? product.image ?? fallbackImages[product.id % fallbackImages.length];
}

function getPriceLabel(price: string) {
  const amount = parseDecimal(price);
  return amount > 0 ? formatINR(amount) : price;
}

function getDiscountLabel(product: ProductCardProduct) {
  if (!product.compareAtPrice) {
    return null;
  }
  const price = parseDecimal(product.price);
  const compareAt = parseDecimal(product.compareAtPrice);
  if (!price || !compareAt || compareAt <= price) {
    return null;
  }
  return `${Math.round(((compareAt - price) / compareAt) * 100)}% off`;
}

function ProductRating({ rating, count }: { rating?: number; count?: number }) {
  if (!rating && !count) {
    return null;
  }

  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-warning-50 px-2 py-1 text-xs font-semibold text-warning-800 dark:bg-warning-900/30 dark:text-warning-300">
      <Star className="h-3.5 w-3.5 fill-warning-500 text-warning-500" aria-hidden="true" />
      {rating ? rating.toFixed(1) : "New"}
      {count ? <span className="font-medium text-warning-700/80 dark:text-warning-200/80">({count})</span> : null}
    </span>
  );
}

export function ProductCard({
  product,
  href,
  imageSrc,
  priority = false,
  className,
  actionLabel = "Add to cart",
  onAddToCart,
  isAdding = false,
  showWishlist = false,
  onWishlist,
}: ProductCardProps) {
  const productHref = href ?? (product.slug ? `/products/${product.slug}` : `/products?q=${encodeURIComponent(product.name)}`);
  const resolvedImage = getProductImage(product, imageSrc);
  const discountLabel = getDiscountLabel(product);
  const isOutOfStock = product.stock_quantity !== undefined && product.stock_quantity <= 0;
  const stockLabel = isOutOfStock ? "Out of stock" : product.stock_quantity !== undefined ? "In stock" : "Ready to ship";
  const priceLabel = getPriceLabel(product.price);
  const compareAtLabel = product.compareAtPrice ? getPriceLabel(product.compareAtPrice) : null;

  return (
    <article
      className={cn(
        "group flex h-full flex-col overflow-hidden rounded-2xl border border-surface-200 bg-white shadow-sm transition-[border-color,box-shadow,transform] motion-slow motion-safe:hover:-translate-y-0.5 hover:border-primary-200 hover:shadow-lg hover:shadow-primary-900/10 dark:border-surface-800 dark:bg-surface-900",
        className,
      )}
    >
      <div className="relative overflow-hidden bg-surface-100 dark:bg-surface-800">
        <Link
          href={productHref}
          className="block focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2"
          aria-label={`View ${product.name}`}
        >
          <div className="relative aspect-[4/3]">
            <Image
              src={resolvedImage}
              alt={product.name}
              fill
              sizes="(max-width: 640px) 92vw, (max-width: 1024px) 45vw, 25vw"
              className="object-cover transition-transform motion-slow group-hover:scale-[1.025]"
              priority={priority}
            />
          </div>
        </Link>

        <div className="absolute left-3 top-3 flex flex-wrap gap-2">
          {discountLabel ? (
            <span className="rounded-full bg-error-600 px-2.5 py-1 text-xs font-bold text-white shadow-sm">
              {discountLabel}
            </span>
          ) : null}
          {product.badge || product.is_refurbished ? (
            <span className="rounded-full bg-white/90 px-2.5 py-1 text-xs font-semibold text-surface-800 shadow-sm backdrop-blur dark:bg-surface-950/85 dark:text-surface-100">
              {product.badge ?? "Refurbished"}
            </span>
          ) : null}
        </div>

        {showWishlist && onWishlist ? (
          <button
            type="button"
            aria-label={`Save ${product.name}`}
            onClick={onWishlist}
            className="tap-highlight-none absolute right-3 top-3 flex h-9 w-9 items-center justify-center rounded-full bg-white/90 text-surface-700 shadow-sm backdrop-blur transition-[color,transform,background-color] motion-standard motion-safe:hover:scale-105 motion-safe:active:scale-95 hover:text-error-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2 dark:bg-surface-950/85 dark:text-surface-100"
          >
            <Heart className="h-4 w-4" aria-hidden="true" />
          </button>
        ) : null}
      </div>

      <div className="flex flex-1 flex-col p-4">
        <div className="flex items-center justify-between gap-2">
          <span className="truncate text-xs font-semibold uppercase tracking-wide text-primary-700 dark:text-primary-300">
            {product.category_name ?? "Premium pick"}
          </span>
          <ProductRating rating={product.average_rating} count={product.reviews_count} />
        </div>

        <h3 className="mt-3 line-clamp-2 min-h-11 text-base font-bold leading-snug text-surface-950 dark:text-white">
          <Link href={productHref} className="rounded-sm transition-colors motion-standard hover:text-primary-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2 dark:hover:text-primary-300">
            {product.name}
          </Link>
        </h3>

        {product.description ? (
          <p className="mt-2 line-clamp-2 min-h-10 text-sm leading-5 text-surface-600 dark:text-surface-300">
            {product.description}
          </p>
        ) : null}

        <div className="mt-4 flex items-end justify-between gap-3">
          <div>
            <data value={parseDecimal(product.price)} className="text-lg font-black text-surface-950 dark:text-white">
              {priceLabel}
            </data>
            {compareAtLabel ? (
              <p className="text-xs font-medium text-surface-500 line-through dark:text-surface-400">{compareAtLabel}</p>
            ) : null}
          </div>
          <span
            className={cn(
              "inline-flex items-center gap-1 rounded-full px-2 py-1 text-xs font-semibold",
              isOutOfStock
                ? "bg-error-50 text-error-700 dark:bg-error-900/30 dark:text-error-300"
                : "bg-success-50 text-success-700 dark:bg-success-900/30 dark:text-success-300",
            )}
          >
            <PackageCheck className="h-3.5 w-3.5" aria-hidden="true" />
            {stockLabel}
          </span>
        </div>

        <div className="mt-4 grid gap-2 text-xs font-medium text-surface-500 dark:text-surface-400">
          <span className="inline-flex items-center gap-1.5">
            <Truck className="h-3.5 w-3.5 text-primary-600" aria-hidden="true" />
            Fast delivery
          </span>
          <span className="inline-flex items-center gap-1.5">
            <BadgeCheck className="h-3.5 w-3.5 text-success-600" aria-hidden="true" />
            Quality checked
          </span>
        </div>

        <div className="mt-auto pt-4">
          <Button
            type="button"
            onClick={onAddToCart}
            loading={isAdding}
            disabled={!onAddToCart || isOutOfStock || isAdding}
            className="w-full rounded-full"
            iconLeft={<ShoppingCart className="h-4 w-4" aria-hidden="true" />}
          >
            {isOutOfStock ? "Notify me" : actionLabel}
          </Button>
        </div>
      </div>
    </article>
  );
}

export function ProductCardSkeleton() {
  return (
    <div className="rounded-2xl border border-surface-200 bg-white p-3 dark:border-surface-800 dark:bg-surface-900">
      <Skeleton className="aspect-[4/3] rounded-xl" />
      <Skeleton className="mt-4 h-3 w-24" />
      <Skeleton className="mt-3 h-5 w-4/5" />
      <Skeleton className="mt-2 h-4 w-full" />
      <Skeleton className="mt-2 h-4 w-3/4" />
      <div className="mt-4 flex items-center justify-between">
        <Skeleton className="h-6 w-24" />
        <Skeleton className="h-6 w-20 rounded-full" />
      </div>
      <Skeleton className="mt-5 h-10 rounded-full" />
    </div>
  );
}
