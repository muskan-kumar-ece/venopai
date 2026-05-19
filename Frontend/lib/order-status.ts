export type BadgeVariant = "default" | "success" | "warning" | "danger" | "info";

export const ORDER_STATUS_META: Record<string, { label: string; variant: BadgeVariant }> = {
  pending_payment: { label: "Pending Payment", variant: "warning" },
  payment_processing: { label: "Payment Processing", variant: "info" },
  paid: { label: "Paid", variant: "success" },
  failed: { label: "Failed", variant: "danger" },
  pending: { label: "Pending", variant: "warning" },
  confirmed: { label: "Processing", variant: "info" },
  processing: { label: "Processing", variant: "info" },
  payment_failed: { label: "Payment Failed", variant: "danger" },
  shipped: { label: "Shipped", variant: "info" },
  delivered: { label: "Delivered", variant: "success" },
  cancelled: { label: "Cancelled", variant: "danger" },
  refunded: { label: "Refunded", variant: "default" },
};

export const PAYMENT_STATUS_META: Record<string, { label: string; variant: BadgeVariant }> = {
  pending_payment: { label: "Pending Payment", variant: "warning" },
  payment_processing: { label: "Payment Processing", variant: "info" },
  pending: { label: "Pending", variant: "warning" },
  paid: { label: "Paid", variant: "success" },
  refunded: { label: "Refunded", variant: "default" },
  failed: { label: "Failed", variant: "danger" },
  cancelled: { label: "Cancelled", variant: "danger" },
};
