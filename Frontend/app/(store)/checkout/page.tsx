"use client";

import { useEffect, useRef, useState } from "react";
import type * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  AlertCircle,
  ArrowLeft,
  BadgeCheck,
  CheckCircle2,
  CreditCard,
  LockKeyhole,
  Mail,
  MapPin,
  PackageCheck,
  Phone,
  RotateCcw,
  ShieldCheck,
  Sparkles,
  Truck,
  User,
} from "lucide-react";

import { useCart } from "@/components/providers/cart-context";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { checkoutFromCart } from "@/lib/api/orders";
import { retryPayment, verifyRazorpayPayment } from "@/lib/api/payments";
import { parseDecimal } from "@/lib/cart/cart-utils";
import { captureApiFailure, trackEvent } from "@/lib/observability";

const inrFormatter = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 2 });
const formatCurrencyNumber = (value: number) => inrFormatter.format(value);

type RazorpaySuccessPayload = {
  razorpay_payment_id: string;
  razorpay_order_id: string;
  razorpay_signature: string;
};

type RazorpayFailurePayload = {
  error?: {
    description?: string;
  };
};

type RazorpayCheckoutOptions = {
  key: string;
  amount: number;
  currency: string;
  order_id: string;
  name: string;
  description: string;
  prefill?: {
    name?: string;
    email?: string;
    contact?: string;
  };
  modal?: {
    ondismiss?: () => void;
  };
  handler: (response: RazorpaySuccessPayload) => void | Promise<void>;
};

type RazorpayCheckoutInstance = {
  open: () => void;
  on: (event: "payment.failed", handler: (response: RazorpayFailurePayload) => void) => void;
};

type FieldErrors = Partial<Record<"fullName" | "email", string>>;

const contactHighlights = [
  { icon: ShieldCheck, label: "Encrypted Razorpay payment" },
  { icon: PackageCheck, label: "Inventory reserved during payment" },
  { icon: RotateCcw, label: "Return support after delivery" },
];

const paymentConfidence = [
  { icon: LockKeyhole, title: "Protected payment", copy: "Card, UPI, wallet and netbanking details stay inside Razorpay secure checkout." },
  { icon: BadgeCheck, title: "Order safeguarded", copy: "Your order is created only through the protected checkout session." },
  { icon: Truck, title: "Delivery-ready items", copy: "Stock is checked before payment starts, so unavailable items are caught early." },
];

const loadRazorpayScript = async () => {
  if (typeof window === "undefined") {
    return false;
  }
  const razorpayWindow = window as Window & {
    Razorpay?: new (options: RazorpayCheckoutOptions) => RazorpayCheckoutInstance;
  };
  if (razorpayWindow.Razorpay) {
    return true;
  }

  return new Promise<boolean>((resolve) => {
    const script = document.createElement("script");
    script.src = "https://checkout.razorpay.com/v1/checkout.js";
    script.async = true;
    script.onload = () => resolve(true);
    script.onerror = () => resolve(false);
    document.body.appendChild(script);
  });
};

const formatReservationTime = (value: string) =>
  new Intl.DateTimeFormat("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));

function CheckoutField({
  id,
  label,
  description,
  error,
  ...props
}: {
  id: string;
  label: string;
  description?: string;
  error?: string;
} & React.ComponentProps<typeof Input>) {
  const descriptionId = description ? `${id}-description` : undefined;
  const errorId = error ? `${id}-error` : undefined;

  return (
    <div className="space-y-2">
      <label htmlFor={id} className="block text-sm font-semibold text-surface-800 dark:text-surface-100">
        {label}
      </label>
      <Input
        id={id}
        size="lg"
        state={error ? "error" : "default"}
        aria-invalid={Boolean(error)}
        aria-describedby={[descriptionId, errorId].filter(Boolean).join(" ") || undefined}
        className="rounded-2xl border-surface-300 bg-white text-base shadow-sm transition-all duration-200 placeholder:text-surface-400 focus-visible:ring-primary-500 dark:border-surface-700 dark:bg-surface-950"
        {...props}
      />
      {description ? (
        <p id={descriptionId} className="text-xs leading-5 text-surface-500 dark:text-surface-400">
          {description}
        </p>
      ) : null}
      {error ? (
        <p id={errorId} className="flex items-center gap-1.5 text-xs font-semibold text-error-700 dark:text-error-300">
          <AlertCircle className="h-3.5 w-3.5" aria-hidden="true" />
          {error}
        </p>
      ) : null}
    </div>
  );
}

function CheckoutContent() {
  const {
    cartView,
    items,
    itemCount,
    subtotalAmount,
    isLoading,
    isError,
    error: cartError,
    isMutating,
    refetch,
  } = useCart();
  const router = useRouter();
  const checkoutKeyRef = useRef<string | null>(null);
  const [isPlacingOrder, setIsPlacingOrder] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [address, setAddress] = useState("");
  const [city, setCity] = useState("");
  const [postalCode, setPostalCode] = useState("");
  const [activeOrderId, setActiveOrderId] = useState<number | null>(null);
  const [reservationExpiresAt, setReservationExpiresAt] = useState<string | null>(null);

  const estimatedSavings = subtotalAmount > 0 ? Math.round(subtotalAmount * 0.08) : 0;
  const paymentButtonLabel = isPlacingOrder ? "Opening secure payment..." : "Pay securely with Razorpay";

  const openRazorpayCheckout = async (
    orderId: number,
    payment: { key_id: string; amount: number; currency: string; razorpay_order_id: string },
    customer: { name: string; email: string; contact?: string },
  ) => {
    const scriptLoaded = await loadRazorpayScript();
    const Razorpay = (window as Window & {
      Razorpay?: new (options: RazorpayCheckoutOptions) => RazorpayCheckoutInstance;
    }).Razorpay;
    if (!scriptLoaded || !Razorpay) {
      setError("Unable to load payment gateway. Please try again.");
      setIsPlacingOrder(false);
      return;
    }
    const checkout = new Razorpay({
      key: payment.key_id,
      amount: payment.amount,
      currency: payment.currency,
      order_id: payment.razorpay_order_id,
      name: "Venopai Commerce",
      description: `Payment for order #${orderId}`,
      prefill: customer,
      modal: {
        ondismiss: () => {
          setError("Payment was cancelled. You can retry payment for this pending order.");
          setIsPlacingOrder(false);
        },
      },
      handler: async (response) => {
        try {
          await verifyRazorpayPayment({
            razorpay_payment_id: response.razorpay_payment_id,
            razorpay_order_id: response.razorpay_order_id,
            razorpay_signature: response.razorpay_signature,
          });
          trackEvent("payment_success", { order_id: orderId, razorpay_order_id: response.razorpay_order_id });
          await refetch();
          router.push(`/order-success?order_id=${orderId}`);
        } catch (_verifyError) {
          captureApiFailure(_verifyError, { stage: "verify_payment", order_id: orderId });
          setError(`Payment verification is pending for order #${orderId}. Please retry verification/payment from this page.`);
          setIsPlacingOrder(false);
        }
      },
    });
    checkout.on("payment.failed", (response) => {
      trackEvent("payment_failed", { order_id: orderId, reason: response.error?.description ?? "unknown" });
      setError(response.error?.description ?? "Payment failed. Your reservation is still active for a limited time.");
      setIsPlacingOrder(false);
    });
    checkout.open();
  };

  useEffect(() => {
    checkoutKeyRef.current = null;
  }, [cartView.id, cartView.updated_at, cartView.item_count, cartView.subtotal]);

  if (isLoading) {
    return (
      <Card className="mx-auto max-w-2xl rounded-3xl border-surface-200 bg-white p-6 shadow-sm dark:border-surface-800 dark:bg-surface-900">
        <CardHeader>
          <CardTitle>Loading your cart</CardTitle>
        </CardHeader>
        <CardContent className="mt-3">
          <p className="text-sm text-surface-600 dark:text-surface-300">Fetching your cart items...</p>
        </CardContent>
      </Card>
    );
  }

  if (isError) {
    return (
      <Card className="mx-auto max-w-2xl rounded-3xl border-surface-200 bg-white p-6 shadow-sm dark:border-surface-800 dark:bg-surface-900">
        <CardHeader>
          <CardTitle>Unable to load checkout</CardTitle>
        </CardHeader>
        <CardContent className="mt-4 space-y-4">
          <p className="text-sm text-surface-600 dark:text-surface-300">
            {cartError?.message ?? "We could not load your cart. Please refresh and try again."}
          </p>
          <Button asChild variant="secondary" className="rounded-full">
            <Link href="/">Back to Home</Link>
          </Button>
        </CardContent>
      </Card>
    );
  }

  if (itemCount === 0) {
    return (
      <Card className="mx-auto max-w-2xl rounded-3xl border-surface-200 bg-white p-6 text-center shadow-sm dark:border-surface-800 dark:bg-surface-900">
        <CardHeader>
          <CardTitle>Your cart is empty</CardTitle>
        </CardHeader>
        <CardContent className="mt-4 space-y-4">
          <p className="text-sm text-surface-600 dark:text-surface-300">
            Add products to your cart before proceeding to checkout.
          </p>
          <Button asChild variant="secondary" className="rounded-full">
            <Link href="/products">Continue shopping</Link>
          </Button>
        </CardContent>
      </Card>
    );
  }

  const validateContact = () => {
    const trimmedName = fullName.trim();
    const trimmedEmail = email.trim();
    const nextFieldErrors: FieldErrors = {};

    if (!trimmedName) {
      nextFieldErrors.fullName = "Enter the name for this order.";
    }
    if (!trimmedEmail) {
      nextFieldErrors.email = "Enter an email for payment and order updates.";
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmedEmail)) {
      nextFieldErrors.email = "Enter a valid email address.";
    }

    setFieldErrors(nextFieldErrors);
    return Object.keys(nextFieldErrors).length === 0;
  };

  const handlePlaceOrder = async () => {
    const trimmedName = fullName.trim();
    const trimmedEmail = email.trim();

    if (!validateContact()) {
      setError("Please fix the highlighted details before starting payment.");
      return;
    }
    if (!cartView.id || itemCount === 0) {
      setError("Your cart is empty. Add items before checking out.");
      return;
    }
    if (isMutating) {
      setError("Please wait for cart updates to finish before checkout.");
      return;
    }

    try {
      setIsPlacingOrder(true);
      setError(null);
      setFieldErrors({});

      const idempotencyKey =
        checkoutKeyRef.current ?? `checkout-${cartView.id}-${cartView.updated_at || "unknown"}`;
      checkoutKeyRef.current = idempotencyKey;

      const checkoutSession = await checkoutFromCart({ idempotency_key: idempotencyKey });
      const { order, payment } = checkoutSession;
      trackEvent("checkout_started", { order_id: order.id, item_count: itemCount });
      setActiveOrderId(order.id);
      setReservationExpiresAt(checkoutSession.reservation_expires_at ?? order.reservation_expires_at ?? null);
      if (checkoutSession.reservation_expires_at && new Date(checkoutSession.reservation_expires_at).getTime() < Date.now()) {
        setError("Reservation expired before payment started. Please retry checkout.");
        setIsPlacingOrder(false);
        return;
      }

      await openRazorpayCheckout(order.id, payment, { name: trimmedName, email: trimmedEmail, contact: phone.trim() || undefined });
    } catch (err) {
      console.error("Failed to place order:", err);
      captureApiFailure(err, { stage: "checkout_from_cart" });
      const apiError = err as { response?: { data?: { detail?: string; order_id?: number } } };
      if (apiError.response?.data?.detail) {
        const detail = apiError.response.data.detail;
        const orderId = apiError.response.data.order_id;
        setError(orderId ? `${detail} (Order #${orderId})` : detail);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Checkout failed. Please try again.");
      }
      setIsPlacingOrder(false);
    }
  };

  const handleRetryPayment = async () => {
    if (!activeOrderId) {
      setError("No pending order found to retry.");
      return;
    }
    try {
      setIsPlacingOrder(true);
      setError(null);
      const session = await retryPayment(String(activeOrderId));
      await openRazorpayCheckout(activeOrderId, session, { name: fullName.trim(), email: email.trim(), contact: phone.trim() || undefined });
    } catch (retryErr) {
      captureApiFailure(retryErr, { stage: "retry_payment", order_id: activeOrderId });
      const apiError = retryErr as { response?: { data?: { detail?: string } } };
      setError(apiError.response?.data?.detail ?? "Unable to retry payment.");
      setIsPlacingOrder(false);
    }
  };

  return (
    <div className="mx-auto w-full max-w-6xl space-y-6 pb-[calc(7rem+env(safe-area-inset-bottom))] lg:pb-0">
      <section className="rounded-3xl border border-surface-200 bg-white p-5 shadow-sm dark:border-surface-800 dark:bg-surface-900 sm:p-6">
        <Link
          href="/cart"
          className="inline-flex items-center gap-2 text-sm font-semibold text-primary-700 hover:text-primary-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2 dark:text-primary-300"
        >
          <ArrowLeft className="h-4 w-4" aria-hidden="true" />
          Back to cart
        </Link>
        <div className="mt-5 grid gap-5 lg:grid-cols-[1fr_auto] lg:items-end">
          <div>
            <p className="text-sm font-semibold uppercase tracking-wide text-primary-700 dark:text-primary-300">
              Secure checkout
            </p>
            <h1 className="mt-2 text-3xl font-black tracking-tight text-surface-950 dark:text-white sm:text-4xl">
              Complete your order with confidence.
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-surface-600 dark:text-surface-300">
              Review your contact details, confirm the total, and continue to Razorpay protected payment window.
            </p>
          </div>
          <div className="grid gap-2 sm:grid-cols-3 lg:w-[520px]">
            {contactHighlights.map((item) => {
              const Icon = item.icon;
              return (
                <div key={item.label} className="rounded-2xl bg-surface-100 p-3 text-xs font-bold text-surface-700 dark:bg-surface-800 dark:text-surface-200">
                  <Icon className="mb-2 h-4 w-4 text-primary-600 dark:text-primary-300" aria-hidden="true" />
                  {item.label}
                </div>
              );
            })}
          </div>
        </div>
      </section>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_390px]">
        <div className="space-y-5">
          <Card className="rounded-3xl border-surface-200 bg-white p-5 shadow-sm dark:border-surface-800 dark:bg-surface-900 sm:p-6">
            <CardHeader className="space-y-2">
              <div className="flex items-start gap-3">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-primary-50 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300">
                  <User className="h-5 w-5" aria-hidden="true" />
                </div>
                <div>
                  <CardTitle className="text-xl font-black">Contact details</CardTitle>
                  <p className="mt-1 text-sm leading-6 text-surface-500 dark:text-surface-400">
                    Used for payment prefill and order updates.
                  </p>
                </div>
              </div>
            </CardHeader>
            <CardContent className="mt-5 grid gap-4 sm:grid-cols-2">
              <div className="sm:col-span-2">
                <CheckoutField
                  id="fullName"
                  label="Full name"
                  placeholder="John Doe"
                  value={fullName}
                  autoComplete="name"
                  inputMode="text"
                  icon={<User className="h-4 w-4" aria-hidden="true" />}
                  error={fieldErrors.fullName}
                  onChange={(event) => setFullName(event.target.value)}
                />
              </div>
              <CheckoutField
                id="email"
                label="Email"
                type="email"
                placeholder="john@example.com"
                value={email}
                autoComplete="email"
                inputMode="email"
                icon={<Mail className="h-4 w-4" aria-hidden="true" />}
                error={fieldErrors.email}
                onChange={(event) => setEmail(event.target.value)}
              />
              <CheckoutField
                id="phone"
                label="Phone"
                type="tel"
                placeholder="+91 98765 43210"
                value={phone}
                autoComplete="tel"
                inputMode="tel"
                icon={<Phone className="h-4 w-4" aria-hidden="true" />}
                description="Optional, helps prefill Razorpay contact."
                onChange={(event) => setPhone(event.target.value)}
              />
            </CardContent>
          </Card>

          <Card className="rounded-3xl border-surface-200 bg-white p-5 shadow-sm dark:border-surface-800 dark:bg-surface-900 sm:p-6">
            <CardHeader>
              <div className="flex items-start gap-3">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-success-50 text-success-700 dark:bg-success-900/30 dark:text-success-300">
                  <MapPin className="h-5 w-5" aria-hidden="true" />
                </div>
                <div>
                  <CardTitle className="text-xl font-black">Delivery context</CardTitle>
                  <p className="mt-1 text-sm leading-6 text-surface-500 dark:text-surface-400">
                    Optional details to keep checkout calm while payment remains unchanged.
                  </p>
                </div>
              </div>
            </CardHeader>
            <CardContent className="mt-5 grid gap-4 sm:grid-cols-2">
              <div className="sm:col-span-2">
                <CheckoutField
                  id="address"
                  label="Address"
                  placeholder="Street address"
                  value={address}
                  autoComplete="street-address"
                  icon={<MapPin className="h-4 w-4" aria-hidden="true" />}
                  description="Delivery address capture is kept optional in this checkout flow."
                  onChange={(event) => setAddress(event.target.value)}
                />
              </div>
              <CheckoutField
                id="city"
                label="City"
                placeholder="Mumbai"
                value={city}
                autoComplete="address-level2"
                onChange={(event) => setCity(event.target.value)}
              />
              <CheckoutField
                id="postalCode"
                label="Postal code"
                placeholder="400001"
                value={postalCode}
                autoComplete="postal-code"
                inputMode="numeric"
                onChange={(event) => setPostalCode(event.target.value)}
              />
            </CardContent>
          </Card>

          <Card className="rounded-3xl border-surface-200 bg-white p-5 shadow-sm dark:border-surface-800 dark:bg-surface-900 sm:p-6">
            <CardHeader>
              <div className="flex items-start gap-3">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-surface-100 text-surface-700 dark:bg-surface-800 dark:text-surface-200">
                  <CreditCard className="h-5 w-5" aria-hidden="true" />
                </div>
                <div>
                  <CardTitle className="text-xl font-black">Payment protection</CardTitle>
                  <p className="mt-1 text-sm leading-6 text-surface-500 dark:text-surface-400">
                    Subtle safeguards before you enter payment details.
                  </p>
                </div>
              </div>
            </CardHeader>
            <CardContent className="mt-5 grid gap-3 md:grid-cols-3">
              {paymentConfidence.map((item) => {
                const Icon = item.icon;
                return (
                  <div key={item.title} className="rounded-2xl border border-surface-200 bg-surface-50 p-4 dark:border-surface-800 dark:bg-surface-950">
                    <Icon className="h-5 w-5 text-primary-600 dark:text-primary-300" aria-hidden="true" />
                    <p className="mt-3 text-sm font-black text-surface-950 dark:text-white">{item.title}</p>
                    <p className="mt-2 text-xs leading-5 text-surface-500 dark:text-surface-400">{item.copy}</p>
                  </div>
                );
              })}
            </CardContent>
          </Card>
        </div>

        <aside className="lg:sticky lg:top-32 lg:self-start">
          <Card className="rounded-3xl border-surface-200 bg-white p-5 shadow-sm dark:border-surface-800 dark:bg-surface-900">
            <CardHeader>
              <div className="flex items-center justify-between gap-3">
                <div>
                  <CardTitle className="text-xl font-black">Order summary</CardTitle>
                  <p className="mt-1 text-sm text-surface-500 dark:text-surface-400">
                    {itemCount} {itemCount === 1 ? "item" : "items"} ready for payment.
                  </p>
                </div>
                <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-primary-50 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300">
                  <Sparkles className="h-5 w-5" aria-hidden="true" />
                </div>
              </div>
            </CardHeader>
            <CardContent className="mt-5 space-y-5">
              <div className="max-h-[280px] space-y-3 overflow-auto pr-1">
                {items.map((item) => {
                  const lineTotal =
                    parseDecimal(item.line_total) ||
                    parseDecimal(item.product.price) * item.quantity;

                  return (
                    <div key={item.id} className="flex items-start justify-between gap-3 rounded-2xl bg-surface-50 p-3 dark:bg-surface-950">
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-bold text-surface-900 dark:text-surface-100">{item.product.name}</p>
                        <p className="mt-1 text-xs text-surface-500 dark:text-surface-400">
                          Qty {item.quantity} x {formatCurrencyNumber(parseDecimal(item.product.price))}
                        </p>
                      </div>
                      <p className="text-sm font-black text-surface-950 dark:text-white">{formatCurrencyNumber(lineTotal)}</p>
                    </div>
                  );
                })}
              </div>

              <div className="space-y-3 border-y border-surface-200 py-4 text-sm dark:border-surface-800">
                <div className="flex items-center justify-between">
                  <span className="text-surface-600 dark:text-surface-300">Subtotal</span>
                  <span className="font-bold text-surface-950 dark:text-white">{formatCurrencyNumber(subtotalAmount)}</span>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <span className="text-surface-600 dark:text-surface-300">Estimated delivery</span>
                  <span className="text-right font-bold text-success-700 dark:text-success-300">Calculated after confirmation</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-surface-600 dark:text-surface-300">Estimated catalog savings</span>
                  <span className="font-bold text-success-700 dark:text-success-300">{formatCurrencyNumber(estimatedSavings)}</span>
                </div>
              </div>

              <div className="flex items-end justify-between gap-3">
                <span className="text-sm font-semibold text-surface-600 dark:text-surface-300">Payable now</span>
                <span className="text-2xl font-black text-surface-950 dark:text-white">{formatCurrencyNumber(subtotalAmount)}</span>
              </div>

              {error ? (
                <Alert variant="error" className="rounded-2xl border-l-0">
                  <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
                  <div>
                    <AlertTitle>Checkout needs attention</AlertTitle>
                    <AlertDescription className="mt-1">{error}</AlertDescription>
                  </div>
                </Alert>
              ) : null}

              {reservationExpiresAt ? (
                <div className="rounded-2xl bg-warning-50 p-3 text-xs font-semibold leading-5 text-warning-800 dark:bg-warning-900/20 dark:text-warning-200">
                  Reservation valid until {formatReservationTime(reservationExpiresAt)}.
                </div>
              ) : null}

              <Button
                type="button"
                fullWidth
                size="lg"
                loading={isPlacingOrder}
                onClick={handlePlaceOrder}
                disabled={isPlacingOrder || isMutating || itemCount === 0}
                className="rounded-full"
                iconLeft={<LockKeyhole className="h-4 w-4" aria-hidden="true" />}
              >
                {paymentButtonLabel}
              </Button>

              {activeOrderId ? (
                <Button
                  type="button"
                  variant="secondary"
                  fullWidth
                  onClick={handleRetryPayment}
                  disabled={isPlacingOrder}
                  className="rounded-full"
                >
                  Retry pending payment
                </Button>
              ) : null}

              <div className="grid gap-2 rounded-2xl bg-surface-50 p-4 text-xs leading-5 text-surface-500 dark:bg-surface-950 dark:text-surface-400">
                <span className="inline-flex items-center gap-2 font-bold text-surface-800 dark:text-surface-100">
                  <CheckCircle2 className="h-4 w-4 text-success-600" aria-hidden="true" />
                  No card details are stored by Venopai.
                </span>
                <span>Payment opens in Razorpay with encrypted transaction handling.</span>
              </div>
            </CardContent>
          </Card>
        </aside>
      </div>

      <div className="fixed inset-x-0 bottom-0 z-40 border-t border-surface-200 bg-white/95 p-3 pb-[calc(0.75rem+env(safe-area-inset-bottom))] shadow-2xl backdrop-blur dark:border-surface-800 dark:bg-neutral-950/95 lg:hidden">
        <div className="mx-auto flex max-w-[1280px] items-center gap-3">
          <div className="min-w-0 flex-1">
            <p className="text-xs font-semibold text-surface-500 dark:text-surface-400">Payable now</p>
            <p className="truncate text-lg font-black text-surface-950 dark:text-white">{formatCurrencyNumber(subtotalAmount)}</p>
          </div>
          <Button
            type="button"
            loading={isPlacingOrder}
            onClick={handlePlaceOrder}
            disabled={isPlacingOrder || isMutating || itemCount === 0}
            className="rounded-full"
          >
            Pay securely
          </Button>
        </div>
      </div>
    </div>
  );
}

export default function CheckoutPage() {
  return <CheckoutContent />;
}
