import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

interface LoadingSkeletonProps {
  variant?: "card" | "list" | "text" | "image" | "page" | "form";
  count?: number;
  className?: string;
}

const LoadingSkeleton = ({ variant = "card", count = 1, className }: LoadingSkeletonProps) => {
  if (variant === "page") {
    return (
      <div className={cn("space-y-6", className)} aria-label="Loading page content">
        <div className="rounded-3xl border border-surface-200 bg-white p-5 shadow-sm dark:border-surface-800 dark:bg-surface-900 sm:p-6">
          <Skeleton className="h-5 w-32 rounded-full" />
          <Skeleton className="mt-5 h-10 w-full max-w-xl" />
          <Skeleton className="mt-3 h-5 w-full max-w-2xl" />
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: count }).map((_, index) => (
            <LoadingSkeleton key={index} variant="card" />
          ))}
        </div>
      </div>
    );
  }

  if (variant === "form") {
    return (
      <div className={cn("rounded-3xl border border-surface-200 bg-white p-5 shadow-sm dark:border-surface-800 dark:bg-surface-900", className)}>
        <Skeleton className="h-7 w-44" />
        <div className="mt-6 space-y-4">
          {Array.from({ length: count }).map((_, index) => (
            <Skeleton key={index} className="h-14 rounded-2xl" />
          ))}
          <Skeleton className="h-12 rounded-full" />
        </div>
      </div>
    );
  }

  if (variant === "list") {
    return (
      <div className={cn("space-y-3", className)} aria-label="Loading list">
        {Array.from({ length: count }).map((_, index) => (
          <Skeleton key={index} className="h-16 w-full rounded-2xl" />
        ))}
      </div>
    );
  }

  if (variant === "text") {
    return <Skeleton className={cn("h-4 w-3/4", className)} />;
  }

  if (variant === "image") {
    return <Skeleton className={cn("aspect-square w-full rounded-3xl", className)} />;
  }

  return (
    <div className={cn("rounded-3xl border border-surface-200 bg-white p-4 shadow-sm dark:border-surface-800 dark:bg-surface-900", className)}>
      <Skeleton className="aspect-[4/3] rounded-2xl" />
      <Skeleton className="mt-4 h-3 w-24" />
      <Skeleton className="mt-3 h-5 w-4/5" />
      <Skeleton className="mt-2 h-4 w-full" />
      <Skeleton className="mt-2 h-4 w-3/4" />
      <div className="mt-5 flex items-center justify-between">
        <Skeleton className="h-6 w-24" />
        <Skeleton className="h-6 w-20 rounded-full" />
      </div>
      <Skeleton className="mt-5 h-10 rounded-full" />
    </div>
  );
};

export { LoadingSkeleton };
