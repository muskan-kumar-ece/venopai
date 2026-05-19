"use client";

import Link from "next/link";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Heart, LockKeyhole } from "lucide-react";

import { useAuth } from "@/components/providers/auth-provider";
import { useCart } from "@/components/providers/cart-context";
import { EmptyState } from "@/components/feedback/empty-state";
import { ErrorState } from "@/components/feedback/error-state";
import { LoadingSkeleton } from "@/components/feedback/loading-skeleton";
import { WishlistCard } from "@/components/wishlist/wishlist-card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { fetchWishlist, removeFromWishlist } from "@/lib/api/wishlist";
import type { WishlistItem } from "@/lib/api/types";

export default function WishlistPage() {
  const { accessToken } = useAuth();
  const queryClient = useQueryClient();
  const { addToCart } = useCart();
  const [removingProductId, setRemovingProductId] = useState<number | null>(null);

  const { data: wishlist = [], isLoading, isError, refetch, isFetching } = useQuery({
    queryKey: ["wishlist"],
    queryFn: fetchWishlist,
    enabled: Boolean(accessToken),
  });

  const removeMutation = useMutation({
    mutationFn: (productId: number) => removeFromWishlist(productId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["wishlist"] });
    },
  });

  const handleMoveToCart = async (item: WishlistItem) => {
    addToCart({
      id: item.product_details?.id ?? item.product,
      name: item.product_details?.name ?? item.product_name ?? `Product #${item.product}`,
      price: item.product_details?.price ?? item.product_price ?? "0",
    });
    setRemovingProductId(item.product);
    try {
      await removeMutation.mutateAsync(item.product);
    } finally {
      setRemovingProductId(null);
    }
  };

  const handleRemove = async (productId: number) => {
    setRemovingProductId(productId);
    try {
      await removeMutation.mutateAsync(productId);
    } finally {
      setRemovingProductId(null);
    }
  };

  if (!accessToken) {
    return (
      <EmptyState
        eyebrow="Wishlist"
        title="Sign in to view saved products"
        description="Your wishlist is connected to your account so saved products stay available across checkout and future visits."
        icon={<LockKeyhole className="h-7 w-7" aria-hidden="true" />}
        className="mx-auto max-w-2xl"
        action={
          <Button asChild className="rounded-full">
          <Link href="/login">Go to Login</Link>
          </Button>
        }
      />
    );
  }

  if (isError) {
    return (
      <ErrorState
        title="Unable to load wishlist"
        description="Your saved products could not be fetched right now. Retry to reconnect your account state."
        onRetry={() => void refetch()}
        isRetrying={isFetching}
      />
    );
  }
  if (isLoading) {
    return <LoadingSkeleton variant="page" count={6} />;
  }

  if (wishlist.length === 0) {
    return (
      <EmptyState
        eyebrow="Wishlist"
        title="No saved products yet"
        description="Save products you are comparing and come back when you are ready to buy."
        icon={<Heart className="h-7 w-7" aria-hidden="true" />}
        className="mx-auto max-w-2xl"
        action={
          <Button asChild className="rounded-full">
            <Link href="/products">Continue Shopping</Link>
          </Button>
        }
        secondaryAction={
          <Button asChild variant="secondary" className="rounded-full">
            <Link href="/">Explore featured</Link>
          </Button>
        }
      />
    );
  }

  return (
    <section className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-3xl font-semibold tracking-tight text-neutral-900 dark:text-neutral-100">Your Wishlist</h1>
        <Badge>{wishlist.length} saved</Badge>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {wishlist.map((item) => (
          <WishlistCard
            key={item.id}
            item={item}
            onRemove={handleRemove}
            onMoveToCart={handleMoveToCart}
            isRemoving={removingProductId === item.product}
          />
        ))}
      </div>
    </section>
  );
}
