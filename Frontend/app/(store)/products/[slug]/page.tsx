"use client";

import Image from "next/image";
import Link from "next/link";
import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  BadgeCheck,
  ChevronRight,
  HeartHandshake,
  Minus,
  PackageCheck,
  Plus,
  RotateCcw,
  ShieldCheck,
  ShoppingCart,
  Star,
  Truck,
} from "lucide-react";

import { useAuth } from "@/components/providers/auth-provider";
import { useCartUI } from "@/components/providers/cart-context";
import { ReviewCard } from "@/components/reviews/review-card";
import { ReviewForm } from "@/components/reviews/review-form";
import { WishlistButton } from "@/components/wishlist/wishlist-button";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { fetchProductBySlug } from "@/lib/api/products";
import { createProductReview, fetchProductReviews, updateProductReview } from "@/lib/api/reviews";
import { formatINR, parseDecimal } from "@/lib/cart/cart-utils";
import { useCart } from "@/lib/cart/use-cart";
import { cn } from "@/lib/utils";

const galleryImages = [
  "https://images.unsplash.com/photo-1516321318423-f06f85e504b3?auto=format&fit=crop&w=1200&q=80",
  "https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=1200&q=80",
  "https://images.unsplash.com/photo-1606220588913-b3aacb4d2f46?auto=format&fit=crop&w=1200&q=80",
  "https://images.unsplash.com/photo-1507473885765-e6ed057f782c?auto=format&fit=crop&w=1200&q=80",
];

function ProductDetailSkeleton() {
  return (
    <div className="grid gap-8 lg:grid-cols-[1.05fr_0.95fr]">
      <Skeleton className="aspect-square rounded-3xl" />
      <div className="space-y-4">
        <Skeleton className="h-5 w-36" />
        <Skeleton className="h-10 w-4/5" />
        <Skeleton className="h-6 w-32" />
        <Skeleton className="h-28 rounded-3xl" />
        <Skeleton className="h-12 rounded-full" />
      </div>
    </div>
  );
}

function RatingStars({ rating }: { rating: number }) {
  return (
    <span className="flex items-center gap-0.5" aria-hidden="true">
      {Array.from({ length: 5 }, (_, index) => (
        <Star
          key={index}
          className={cn(
            "h-4 w-4",
            index < Math.round(rating) ? "fill-warning-500 text-warning-500" : "text-surface-300 dark:text-surface-600",
          )}
        />
      ))}
    </span>
  );
}

function QuantityControl({
  quantity,
  setQuantity,
  max,
}: {
  quantity: number;
  setQuantity: (quantity: number) => void;
  max: number;
}) {
  return (
    <div className="inline-flex h-11 items-center rounded-full border border-surface-300 bg-white p-1 dark:border-surface-700 dark:bg-surface-950">
      <button
        type="button"
        aria-label="Decrease quantity"
        onClick={() => setQuantity(Math.max(1, quantity - 1))}
        className="flex h-9 w-9 items-center justify-center rounded-full text-surface-700 transition-colors hover:bg-surface-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 dark:text-surface-200 dark:hover:bg-surface-800"
      >
        <Minus className="h-4 w-4" aria-hidden="true" />
      </button>
      <span className="w-10 text-center text-sm font-bold text-surface-950 dark:text-white" aria-live="polite">
        {quantity}
      </span>
      <button
        type="button"
        aria-label="Increase quantity"
        onClick={() => setQuantity(Math.min(max, quantity + 1))}
        className="flex h-9 w-9 items-center justify-center rounded-full text-surface-700 transition-colors hover:bg-surface-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 dark:text-surface-200 dark:hover:bg-surface-800"
      >
        <Plus className="h-4 w-4" aria-hidden="true" />
      </button>
    </div>
  );
}

export default function ProductDetailPage({ params }: { params: { slug: string } }) {
  const { accessToken } = useAuth();
  const { openDrawer } = useCartUI();
  const { addToCart, isMutating } = useCart();
  const queryClient = useQueryClient();
  const [selectedImage, setSelectedImage] = useState(0);
  const [quantity, setQuantity] = useState(1);

  const { data: product, isLoading, isError } = useQuery({
    queryKey: ["product", params.slug],
    queryFn: () => fetchProductBySlug(params.slug),
  });

  const {
    data: reviews = [],
    isLoading: isReviewsLoading,
    isError: isReviewsError,
  } = useQuery({
    queryKey: ["product-reviews", product?.id],
    queryFn: () => fetchProductReviews(product!.id),
    enabled: Boolean(product?.id),
  });

  const reviewMutation = useMutation({
    mutationFn: ({ rating, title, comment }: { rating: number; title: string; comment: string }) => {
      const existingReview = reviews.find((review) => review.is_mine);
      if (existingReview) {
        return updateProductReview(existingReview.id, product!.id, rating, title, comment);
      }
      return createProductReview(product!.id, rating, title, comment);
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["product-reviews", product?.id] });
      await queryClient.invalidateQueries({ queryKey: ["product", params.slug] });
    },
  });

  const productImages = useMemo(() => {
    if (!product) {
      return galleryImages;
    }
    if (product.images?.length) {
      return product.images.map((image) => image.image_url_detail ?? image.image_url);
    }
    if (product.image_url_detail ?? product.image_url) {
      return [product.image_url_detail ?? product.image_url!];
    }
    const offset = product.id % galleryImages.length;
    return [...galleryImages.slice(offset), ...galleryImages.slice(0, offset)];
  }, [product]);

  if (isError) {
    return (
      <section className="rounded-3xl border border-error-200 bg-error-50 p-6 text-sm text-error-700 dark:border-error-900/50 dark:bg-error-900/20 dark:text-error-300">
        Unable to load product details.
      </section>
    );
  }

  if (isLoading || !product) {
    return <ProductDetailSkeleton />;
  }

  const averageRating = Number(product.average_rating ?? 0);
  const averageRatingLabel = averageRating ? averageRating.toFixed(1) : "New";
  const reviewsCount = product.reviews_count ?? reviews.length;
  const myReview = reviews.find((review) => review.is_mine);
  const priceValue = parseDecimal(product.price);
  const compareAtPrice = priceValue ? priceValue * 1.18 : 0;
  const discountPercent = compareAtPrice ? Math.round(((compareAtPrice - priceValue) / compareAtPrice) * 100) : 0;
  const inStock = product.stock_quantity > 0;
  const maxQuantity = Math.max(1, Math.min(product.stock_quantity || 1, 10));

  const addProductToCart = async () => {
    await addToCart(product.id, quantity, {
      id: product.id,
      name: product.name,
      slug: product.slug,
      sku: product.sku,
      price: product.price,
      stock_quantity: product.stock_quantity,
      is_active: product.is_active,
      is_refurbished: product.is_refurbished,
      condition_grade: product.condition_grade,
      category_name: product.category_name,
      image_url: product.image_url_card ?? product.image_url ?? null,
      image_url_card: product.image_url_card ?? null,
    });
    openDrawer();
  };

  return (
    <div className="space-y-8 pb-[calc(7rem+env(safe-area-inset-bottom))] lg:space-y-10 lg:pb-0">
      <nav aria-label="Breadcrumb" className="flex flex-wrap items-center gap-2 text-sm text-surface-500 dark:text-surface-400">
        <Link href="/" className="font-medium hover:text-primary-700 dark:hover:text-primary-300">
          Home
        </Link>
        <ChevronRight className="h-4 w-4" aria-hidden="true" />
        <Link href="/products" className="font-medium hover:text-primary-700 dark:hover:text-primary-300">
          Products
        </Link>
        <ChevronRight className="h-4 w-4" aria-hidden="true" />
        <span className="font-semibold text-surface-800 dark:text-surface-100">{product.name}</span>
      </nav>

      <section className="grid gap-6 lg:grid-cols-[1.05fr_0.95fr] lg:items-start xl:gap-8">
        <div className="space-y-4">
          <div className="relative overflow-hidden rounded-[2rem] border border-surface-200 bg-surface-100 shadow-sm dark:border-surface-800 dark:bg-surface-900">
            <div className="relative aspect-square">
              <Image
                src={productImages[selectedImage]}
                alt={product.name}
                fill
                sizes="(max-width: 1024px) 92vw, 52vw"
                className="object-cover"
                priority
              />
            </div>
            <div className="absolute left-4 top-4 flex flex-wrap gap-2">
              {discountPercent ? (
                <Badge variant="danger">{discountPercent}% off</Badge>
              ) : null}
              {product.is_refurbished ? <Badge variant="info">Refurbished</Badge> : null}
            </div>
          </div>

          <div className="grid grid-cols-4 gap-2 sm:gap-3" aria-label="Product image thumbnails">
            {productImages.map((image, index) => (
              <button
                key={image}
                type="button"
                aria-label={`View product image ${index + 1}`}
                aria-pressed={selectedImage === index}
                onClick={() => setSelectedImage(index)}
                className={cn(
                  "relative aspect-square overflow-hidden rounded-xl border bg-surface-100 transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2 dark:bg-surface-900 sm:rounded-2xl",
                  selectedImage === index
                    ? "border-primary-600 shadow-md shadow-primary-900/10"
                    : "border-surface-200 hover:border-primary-200 dark:border-surface-800",
                )}
              >
                <Image src={image} alt="" fill sizes="20vw" className="object-cover" />
              </button>
            ))}
          </div>
        </div>

        <div className="lg:sticky lg:top-36">
          <Card className="rounded-[2rem] border-surface-200 bg-white shadow-sm dark:border-surface-800 dark:bg-surface-900">
            <CardContent className="space-y-6 p-5 sm:p-6">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="info">{product.category_name}</Badge>
                <Badge variant={inStock ? "success" : "danger"} dot>
                  {inStock ? "In stock" : "Out of stock"}
                </Badge>
              </div>

              <div>
                <h1 className="text-3xl font-black tracking-tight text-surface-950 dark:text-white sm:text-4xl">
                  {product.name}
                </h1>
                <p className="mt-3 text-sm text-surface-500 dark:text-surface-400">SKU: {product.sku}</p>
              </div>

              <div className="flex flex-wrap items-center gap-3">
                <span className="inline-flex items-center gap-2 rounded-full bg-warning-50 px-3 py-1.5 text-sm font-bold text-warning-800 dark:bg-warning-900/30 dark:text-warning-300">
                  <RatingStars rating={averageRating} />
                  {averageRatingLabel}
                </span>
                <span className="text-sm font-medium text-surface-500 dark:text-surface-400">
                  {reviewsCount} reviews
                </span>
              </div>

              <div className="rounded-3xl bg-surface-50 p-4 dark:bg-surface-800">
                <div className="flex flex-wrap items-end gap-3">
                  <data value={priceValue} className="text-3xl font-black text-surface-950 dark:text-white">
                    {formatINR(priceValue)}
                  </data>
                  {compareAtPrice ? (
                    <span className="pb-1 text-sm font-medium text-surface-500 line-through dark:text-surface-400">
                      {formatINR(compareAtPrice)}
                    </span>
                  ) : null}
                  {discountPercent ? (
                    <span className="pb-1 text-sm font-bold text-success-700 dark:text-success-300">
                      Save {discountPercent}%
                    </span>
                  ) : null}
                </div>
                <p className="mt-2 text-xs font-medium text-surface-500 dark:text-surface-400">
                  Inclusive of taxes. Secure checkout available at payment.
                </p>
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <div className="rounded-2xl border border-surface-200 p-4 dark:border-surface-700">
                  <Truck className="h-5 w-5 text-primary-600" aria-hidden="true" />
                  <p className="mt-2 text-sm font-bold text-surface-950 dark:text-white">Fast delivery</p>
                  <p className="mt-1 text-xs text-surface-500 dark:text-surface-400">Dispatch-ready inventory where available.</p>
                </div>
                <div className="rounded-2xl border border-surface-200 p-4 dark:border-surface-700">
                  <ShieldCheck className="h-5 w-5 text-success-600" aria-hidden="true" />
                  <p className="mt-2 text-sm font-bold text-surface-950 dark:text-white">Secure purchase</p>
                  <p className="mt-1 text-xs text-surface-500 dark:text-surface-400">Protected cart and payment flow.</p>
                </div>
              </div>

              <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
                <QuantityControl quantity={quantity} setQuantity={setQuantity} max={maxQuantity} />
                <Button
                  type="button"
                  size="lg"
                  className="flex-1 rounded-full"
                  disabled={!inStock || isMutating}
                  loading={isMutating}
                  iconLeft={<ShoppingCart className="h-4 w-4" aria-hidden="true" />}
                  onClick={() => {
                    void addProductToCart();
                  }}
                >
                  {inStock ? "Add to cart" : "Out of stock"}
                </Button>
              </div>

              <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_auto]">
                <WishlistButton productId={product.id} className="rounded-full" />
                <Button asChild variant="outline" className="rounded-full">
                  <Link href="/checkout">Buy now</Link>
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[1fr_360px]">
        <Card className="rounded-3xl border-surface-200 bg-white shadow-sm dark:border-surface-800 dark:bg-surface-900">
          <CardHeader>
            <CardTitle className="text-2xl">Product story</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <p className="text-base leading-7 text-surface-600 dark:text-surface-300">{product.description}</p>
            <div className="grid gap-3 sm:grid-cols-2">
              {[
                ["Condition", product.condition_grade || "Premium checked"],
                ["Category", product.category_name],
                ["Availability", inStock ? `${product.stock_quantity} units available` : "Currently unavailable"],
                ["Product type", product.is_refurbished ? "Refurbished" : "New"],
              ].map(([label, value]) => (
                <div key={label} className="rounded-2xl bg-surface-50 p-4 dark:bg-surface-800">
                  <p className="text-xs font-semibold uppercase tracking-wide text-surface-500 dark:text-surface-400">{label}</p>
                  <p className="mt-1 text-sm font-bold text-surface-950 dark:text-white">{value}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="rounded-3xl border-surface-200 bg-white shadow-sm dark:border-surface-800 dark:bg-surface-900">
          <CardHeader>
            <CardTitle className="text-xl">Why shop this</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-4">
            {[
              { icon: BadgeCheck, title: "Authenticity first", text: "Catalog quality checks before purchase." },
              { icon: RotateCcw, title: "Return assurance", text: "Simple support if something is not right." },
              { icon: PackageCheck, title: "Stock confidence", text: "Inventory status shown before cart." },
              { icon: HeartHandshake, title: "Support ready", text: "Help available through the buying journey." },
            ].map((item) => {
              const Icon = item.icon;
              return (
                <div key={item.title} className="flex gap-3">
                  <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-primary-50 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300">
                    <Icon className="h-5 w-5" aria-hidden="true" />
                  </span>
                  <div>
                    <p className="text-sm font-bold text-surface-950 dark:text-white">{item.title}</p>
                    <p className="mt-1 text-sm leading-5 text-surface-500 dark:text-surface-400">{item.text}</p>
                  </div>
                </div>
              );
            })}
          </CardContent>
        </Card>
      </section>

      <section className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-sm font-semibold uppercase tracking-wide text-primary-700 dark:text-primary-300">Customer proof</p>
            <h2 className="mt-1 text-2xl font-black tracking-tight text-surface-950 dark:text-white">Customer Reviews</h2>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="info">Average: {averageRatingLabel} / 5</Badge>
            <Badge>{reviewsCount} reviews</Badge>
          </div>
        </div>

        {isReviewsLoading && <p className="text-sm text-neutral-500">Loading reviews...</p>}
        {isReviewsError && <p className="text-sm text-rose-600">Unable to load reviews right now.</p>}
        {!isReviewsLoading && !isReviewsError && reviews.length === 0 && (
          <div className="rounded-3xl border border-dashed border-surface-300 bg-white p-6 text-sm text-surface-500 dark:border-surface-700 dark:bg-surface-900 dark:text-surface-300">
            No reviews yet. Be the first to review this product.
          </div>
        )}

        {reviews.length > 0 && (
          <div className="grid gap-4 md:grid-cols-2">
            {reviews.map((review) => (
              <ReviewCard
                key={review.id}
                userName={review.user_name}
                rating={review.rating}
                title={review.title}
                comment={review.comment}
                createdAt={review.created_at}
              />
            ))}
          </div>
        )}

        {accessToken ? (
          <ReviewForm
            onSubmit={async (rating, title, comment) => {
              await reviewMutation.mutateAsync({ rating, title, comment });
            }}
            isSubmitting={reviewMutation.isPending}
            initialRating={myReview?.rating ?? 5}
            initialTitle={myReview?.title ?? ""}
            initialComment={myReview?.comment ?? ""}
            mode={myReview ? "edit" : "create"}
          />
        ) : (
          <Card className="rounded-3xl border-surface-200 bg-white dark:border-surface-800 dark:bg-surface-900">
            <CardContent className="flex flex-col gap-3 p-5 sm:flex-row sm:items-center sm:justify-between">
              <p className="text-sm text-surface-600 dark:text-surface-300">Log in to write a review and save your feedback.</p>
              <Button asChild className="rounded-full">
                <Link href="/login">Log in</Link>
              </Button>
            </CardContent>
          </Card>
        )}
      </section>

      <div className="fixed inset-x-0 bottom-0 z-40 border-t border-surface-200 bg-white/95 p-3 pb-[calc(0.75rem+env(safe-area-inset-bottom))] shadow-2xl backdrop-blur dark:border-surface-800 dark:bg-neutral-950/95 lg:hidden">
        <div className="mx-auto flex max-w-[1280px] items-center gap-3">
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-bold text-surface-950 dark:text-white">{product.name}</p>
            <p className="text-sm font-black text-primary-700 dark:text-primary-300">{formatINR(priceValue)}</p>
          </div>
          <Button
            type="button"
            className="rounded-full"
            disabled={!inStock || isMutating}
            loading={isMutating}
            onClick={() => {
              void addProductToCart();
            }}
          >
            Add to cart
          </Button>
        </div>
      </div>
    </div>
  );
}
