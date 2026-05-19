"use client";

import { BadgeCheck, ShoppingCart, Trash2, Truck } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatProductPrice } from "@/lib/cart/cart-utils";
import type { WishlistItem } from "@/lib/api/types";

type WishlistCardProps = {
  item: WishlistItem;
  onRemove: (productId: number) => void;
  onMoveToCart: (item: WishlistItem) => void;
  isRemoving?: boolean;
};

export function WishlistCard({ item, onRemove, onMoveToCart, isRemoving = false }: WishlistCardProps) {
  const productName = item.product_details?.name ?? item.product_name ?? `Product #${item.product}`;
  const productPrice = item.product_details?.price ?? item.product_price ?? "0";

  return (
    <Card className="group h-full overflow-hidden rounded-2xl border-surface-200 bg-white shadow-sm transition-[border-color,box-shadow,transform] motion-slow motion-safe:hover:-translate-y-0.5 hover:border-primary-200 hover:shadow-lg hover:shadow-primary-900/10 dark:border-surface-800 dark:bg-surface-900">
      <CardContent className="p-0">
        <div
          className="flex aspect-[4/3] items-center justify-center bg-surface-100 bg-cover bg-center text-sm font-medium text-surface-500 transition-transform motion-slow group-hover:scale-[1.02] dark:bg-surface-800 dark:text-surface-400"
          style={item.image_url ? { backgroundImage: `url(${item.image_url})` } : undefined}
          role="img"
          aria-label={productName}
        >
          {!item.image_url && "Product image"}
        </div>
      </CardContent>
      <CardHeader className="space-y-3">
        <div className="flex items-start justify-between gap-3">
          <CardTitle className="text-base leading-snug text-surface-950 dark:text-white">{productName}</CardTitle>
          <Badge variant="info">Saved</Badge>
        </div>
        <div className="flex items-end justify-between gap-3">
          <p className="text-lg font-black text-surface-950 dark:text-white">{formatProductPrice(productPrice)}</p>
          <span className="rounded-full bg-success-50 px-2 py-1 text-xs font-semibold text-success-700 dark:bg-success-900/30 dark:text-success-300">
            In stock
          </span>
        </div>
        <div className="grid gap-1 text-xs font-medium text-surface-500 dark:text-surface-400">
          <span className="inline-flex items-center gap-1.5">
            <Truck className="h-3.5 w-3.5 text-primary-600" aria-hidden="true" />
            Fast delivery
          </span>
          <span className="inline-flex items-center gap-1.5">
            <BadgeCheck className="h-3.5 w-3.5 text-success-600" aria-hidden="true" />
            Quality checked
          </span>
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-2 sm:flex-row">
        <Button
          type="button"
          variant="secondary"
          className="flex-1 rounded-full"
          iconLeft={<ShoppingCart className="h-4 w-4" />}
          onClick={() => onMoveToCart(item)}
        >
          Move to cart
        </Button>
        <Button
          type="button"
          variant="ghost"
          className="flex-1 rounded-full"
          iconLeft={<Trash2 className="h-4 w-4" />}
          onClick={() => onRemove(item.product)}
          loading={isRemoving}
        >
          Remove
        </Button>
      </CardContent>
    </Card>
  );
}
