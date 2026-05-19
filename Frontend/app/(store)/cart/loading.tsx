import { ProductCardSkeleton } from "@/components/products/product-card";
import { Skeleton } from "@/components/ui/skeleton";

export default function CartLoading() {
  return (
    <section className="space-y-6">
      <div className="rounded-3xl border border-surface-200 bg-white p-6 shadow-sm dark:border-surface-800 dark:bg-surface-900">
        <Skeleton className="h-4 w-32 rounded-full" />
        <Skeleton className="mt-4 h-10 w-3/4 max-w-xl" />
        <Skeleton className="mt-3 h-5 w-56" />
      </div>
      <div className="grid gap-6 lg:grid-cols-[1fr_380px]">
        <div className="space-y-4">
          {Array.from({ length: 3 }).map((_, index) => (
            <ProductCardSkeleton key={index} />
          ))}
        </div>
        <div className="rounded-3xl border border-surface-200 bg-white p-5 shadow-sm dark:border-surface-800 dark:bg-surface-900">
          <Skeleton className="h-7 w-40" />
          <Skeleton className="mt-6 h-4 w-full" />
          <Skeleton className="mt-4 h-4 w-full" />
          <Skeleton className="mt-4 h-4 w-full" />
          <Skeleton className="mt-6 h-12 rounded-full" />
        </div>
      </div>
    </section>
  );
}
