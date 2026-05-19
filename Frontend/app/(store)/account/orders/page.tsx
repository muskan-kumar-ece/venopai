"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { PackageSearch } from "lucide-react";

import { EmptyState } from "@/components/feedback/empty-state";
import { ErrorState } from "@/components/feedback/error-state";
import { LoadingSkeleton } from "@/components/feedback/loading-skeleton";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { fetchMyOrders } from "@/lib/api/orders";
import { ORDER_STATUS_META } from "@/lib/order-status";
import { formatOrderNumber } from "@/lib/order-utils";

const currencyFormatter = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 2,
});

const dateFormatter = new Intl.DateTimeFormat("en-IN", {
  day: "2-digit",
  month: "short",
  year: "numeric",
});

const toNumber = (value: string) => {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
};

const getStatusMeta = (status: string) => {
  return ORDER_STATUS_META[status] ?? { label: status, variant: "default" as const };
};

export default function OrdersPage() {
  const { data, isLoading, isError, refetch, isFetching } = useQuery({
    queryKey: ["my-orders"],
    queryFn: async () => {
      const orders = await fetchMyOrders();

      return orders.map((order) => {
        return {
          ...order,
          itemCount: order.items?.reduce((total, item) => total + item.quantity, 0) ?? 0,
          orderNumber: formatOrderNumber(order.id, order.tracking_id),
          statusMeta: getStatusMeta(order.status),
        };
      });
    },
  });

  return (
    <section className="mx-auto w-full max-w-5xl space-y-6">
      <header className="space-y-2">
        <h1 className="text-3xl font-semibold tracking-tight text-neutral-900 dark:text-neutral-100">Your Orders</h1>
        <p className="text-sm text-neutral-600 dark:text-neutral-300">Review past purchases and stay updated on delivery progress.</p>
      </header>

      {isLoading ? (
        <LoadingSkeleton variant="list" count={4} />
      ) : null}

      {isError ? (
        <ErrorState
          title="Unable to load your orders"
          description="Your account order history could not be refreshed. Retry to reconnect this view."
          onRetry={() => void refetch()}
          retryLabel="Try again"
          isRetrying={isFetching}
        />
      ) : null}

      {data && data.length === 0 ? (
        <EmptyState
          eyebrow="Orders"
          title="You have no orders yet"
          description="Explore premium products and place your first order when you are ready."
          icon={<PackageSearch className="h-7 w-7" aria-hidden="true" />}
          action={
            <Button asChild className="rounded-full">
              <Link href="/products">Start shopping</Link>
            </Button>
          }
          secondaryAction={
            <Button asChild variant="secondary" className="rounded-full">
              <Link href="/cart">View cart</Link>
            </Button>
          }
        />
      ) : null}

      {data && data.length > 0 ? (
        <div className="space-y-4">
          {data.map((order) => (
            <Card key={order.id} className="border-neutral-200 shadow-sm transition-shadow hover:shadow-md dark:border-neutral-800">
              <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div className="space-y-1">
                  <CardTitle className="text-xl text-neutral-900 dark:text-neutral-100">{order.orderNumber}</CardTitle>
                  <CardDescription>Ordered on {dateFormatter.format(new Date(order.created_at))}</CardDescription>
                </div>
                <Badge variant={order.statusMeta.variant} dot>
                  {order.statusMeta.label}
                </Badge>
              </CardHeader>
              <CardContent className="space-y-5">
                <div className="grid gap-3 text-sm text-neutral-700 dark:text-neutral-300 sm:grid-cols-2">
                  <p>
                    <span className="text-neutral-500 dark:text-neutral-400">Total Amount:</span>{" "}
                    <span className="font-semibold text-neutral-900 dark:text-neutral-100">
                      {currencyFormatter.format(toNumber(order.total_amount))}
                    </span>
                  </p>
                  <p>
                    <span className="text-neutral-500 dark:text-neutral-400">Number of Items:</span>{" "}
                    <span className="font-semibold text-neutral-900 dark:text-neutral-100">{order.itemCount}</span>
                  </p>
                </div>
                <div className="flex flex-col gap-3 sm:flex-row">
                  <Button asChild>
                    <Link href={`/account/orders/${order.id}`}>View Details</Link>
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : null}
    </section>
  );
}
