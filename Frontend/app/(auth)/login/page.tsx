"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import type * as React from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import {
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  Eye,
  EyeOff,
  LockKeyhole,
  Mail,
  ShieldCheck,
  ShoppingBag,
  Sparkles,
  UserRound,
} from "lucide-react";

import { useAuth } from "@/components/providers/auth-provider";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

type FieldErrors = Partial<Record<"email" | "password", string>>;

const trustCues = [
  { icon: ShieldCheck, label: "Protected sessions" },
  { icon: ShoppingBag, label: "Cart and order continuity" },
  { icon: Sparkles, label: "Faster checkout access" },
];

const accountBenefits = [
  "View orders and payment status in one place.",
  "Keep cart, wishlist, and checkout context connected.",
  "Resume protected sessions without repeating account steps.",
];

function AuthField({
  id,
  label,
  error,
  description,
  ...props
}: {
  id: string;
  label: string;
  error?: string;
  description?: string;
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

function LoginForm() {
  const { login, logoutReason, clearLogoutReason, isReady } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [message, setMessage] = useState<{ type: "success" | "error" | "info"; text: string } | null>(null);
  const router = useRouter();
  const searchParams = useSearchParams();

  const nextPath = useMemo(() => {
    const candidate = searchParams.get("next") ?? "/";
    if (!candidate.startsWith("/") || candidate.startsWith("//")) {
      return "/";
    }
    return candidate;
  }, [searchParams]);

  useEffect(() => {
    const reason = searchParams.get("reason");
    if (reason === "expired") {
      setMessage({ type: "info", text: "Your session expired. Sign in again to continue securely." });
    }
    if (logoutReason === "expired") {
      setMessage({ type: "info", text: "Your session expired. Sign in again to continue securely." });
      clearLogoutReason();
    }
  }, [clearLogoutReason, logoutReason, searchParams]);

  const validateForm = () => {
    const trimmedEmail = email.trim();
    const nextErrors: FieldErrors = {};

    if (!trimmedEmail) {
      nextErrors.email = "Enter your email address.";
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmedEmail)) {
      nextErrors.email = "Enter a valid email address.";
    }

    if (!password) {
      nextErrors.password = "Enter your password.";
    }

    setFieldErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  };

  const loginMutation = useMutation({
    mutationFn: () => login(email.trim(), password),
    onSuccess: () => {
      setMessage({ type: "success", text: "Signed in. Taking you back to your account." });
      router.replace(nextPath);
    },
    onError: () => {
      setMessage({ type: "error", text: "Sign in failed. Check your email and password, then try again." });
    },
  });

  const onSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setMessage(null);
    if (!validateForm()) {
      setMessage({ type: "error", text: "Please fix the highlighted details before signing in." });
      return;
    }
    loginMutation.mutate();
  };

  const alertVariant = message?.type === "error" ? "error" : message?.type === "success" ? "success" : "info";

  return (
    <section className="mx-auto grid w-full max-w-6xl gap-6 px-4 py-6 sm:px-6 sm:py-8 lg:grid-cols-[minmax(0,1fr)_440px] lg:items-center lg:px-8 lg:py-12">
      <div className="rounded-3xl border border-surface-200 bg-white p-5 shadow-sm dark:border-surface-800 dark:bg-surface-900 sm:p-7">
        <Link
          href="/"
          className="inline-flex items-center gap-2 rounded-full bg-surface-100 px-3 py-2 text-sm font-semibold text-surface-700 transition-colors hover:bg-primary-50 hover:text-primary-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2 dark:bg-surface-800 dark:text-surface-200 dark:hover:bg-primary-900/30"
        >
          <span className="flex h-7 w-7 items-center justify-center rounded-full bg-primary-600 text-xs font-black text-white">V</span>
          VenoPai account
        </Link>

        <div className="mt-8 max-w-2xl">
          <p className="text-sm font-semibold uppercase tracking-wide text-primary-700 dark:text-primary-300">Secure sign in</p>
          <h1 className="mt-3 text-3xl font-black tracking-tight text-surface-950 dark:text-white sm:text-4xl lg:text-5xl">
            Continue to a calmer shopping account.
          </h1>
          <p className="mt-4 text-sm leading-6 text-surface-600 dark:text-surface-300 sm:text-base">
            Sign in to keep your cart, orders, wishlist, and checkout access connected across your VenoPai experience.
          </p>
        </div>

        <div className="mt-8 grid gap-3 sm:grid-cols-3 lg:grid-cols-3">
          {trustCues.map((item) => {
            const Icon = item.icon;
            return (
              <div key={item.label} className="rounded-2xl bg-surface-100 p-4 text-sm font-bold text-surface-700 dark:bg-surface-800 dark:text-surface-200">
                <Icon className="mb-3 h-5 w-5 text-primary-600 dark:text-primary-300" aria-hidden="true" />
                {item.label}
              </div>
            );
          })}
        </div>

        <div className="mt-8 rounded-3xl bg-surface-50 p-5 dark:bg-surface-950">
          <p className="text-sm font-black text-surface-950 dark:text-white">Why sign in?</p>
          <div className="mt-4 grid gap-3">
            {accountBenefits.map((benefit) => (
              <div key={benefit} className="flex items-start gap-3 text-sm leading-6 text-surface-600 dark:text-surface-300">
                <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-success-600" aria-hidden="true" />
                <span>{benefit}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <Card className="rounded-3xl border-surface-200 bg-white p-5 shadow-xl shadow-surface-900/5 dark:border-surface-800 dark:bg-surface-900 sm:p-6">
        <CardContent>
          <div className="flex items-start gap-3">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-primary-50 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300">
              <UserRound className="h-5 w-5" aria-hidden="true" />
            </div>
            <div>
              <h2 className="text-2xl font-black tracking-tight text-surface-950 dark:text-white">Sign in</h2>
              <p className="mt-1 text-sm leading-6 text-surface-500 dark:text-surface-400">
                Use your VenoPai account credentials.
              </p>
            </div>
          </div>

          <form onSubmit={onSubmit} className="mt-6 space-y-5" noValidate>
            <AuthField
              id="email"
              label="Email"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="you@example.com"
              autoComplete="email"
              inputMode="email"
              icon={<Mail className="h-4 w-4" aria-hidden="true" />}
              error={fieldErrors.email}
              required
            />

            <div className="space-y-2">
              <AuthField
                id="password"
                label="Password"
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="Enter your password"
                autoComplete="current-password"
                icon={<LockKeyhole className="h-4 w-4" aria-hidden="true" />}
                iconPosition="left"
                error={fieldErrors.password}
                required
              />
              <button
                type="button"
                onClick={() => setShowPassword((current) => !current)}
                className="inline-flex min-h-10 items-center gap-2 rounded-full px-1 text-sm font-semibold text-primary-700 transition-colors hover:text-primary-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2 dark:text-primary-300"
                aria-pressed={showPassword}
              >
                {showPassword ? <EyeOff className="h-4 w-4" aria-hidden="true" /> : <Eye className="h-4 w-4" aria-hidden="true" />}
                {showPassword ? "Hide password" : "Show password"}
              </button>
            </div>

            {message ? (
              <Alert variant={alertVariant} className="rounded-2xl border-l-0">
                {message.type === "success" ? (
                  <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
                ) : (
                  <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
                )}
                <div>
                  <AlertTitle>{message.type === "error" ? "Sign in needs attention" : "Account update"}</AlertTitle>
                  <AlertDescription className="mt-1">{message.text}</AlertDescription>
                </div>
              </Alert>
            ) : null}

            <Button
              type="submit"
              size="lg"
              fullWidth
              loading={loginMutation.isPending}
              disabled={loginMutation.isPending || !isReady}
              className="rounded-full"
              iconRight={<ArrowRight className="h-4 w-4" aria-hidden="true" />}
            >
              {loginMutation.isPending ? "Signing in..." : "Sign in securely"}
            </Button>

            <div className="rounded-2xl bg-surface-50 p-4 text-xs leading-5 text-surface-500 dark:bg-surface-950 dark:text-surface-400">
              <span className="inline-flex items-center gap-2 font-bold text-surface-800 dark:text-surface-100">
                <ShieldCheck className="h-4 w-4 text-success-600" aria-hidden="true" />
                Your session is protected by token-based authentication.
              </span>
              <p className="mt-2">We use your account only to keep commerce actions and order access connected.</p>
            </div>

            <p className="text-center text-sm text-surface-500 dark:text-surface-400">
              Need access?{" "}
              <Link href="/register" className="font-semibold text-primary-700 hover:text-primary-800 dark:text-primary-300">
                View account availability
              </Link>
            </p>
          </form>
        </CardContent>
      </Card>
    </section>
  );
}

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <div className="mx-auto grid w-full max-w-6xl gap-6 px-4 py-6 sm:px-6 sm:py-8 lg:grid-cols-[minmax(0,1fr)_440px] lg:px-8 lg:py-12">
          <div className="h-[520px] rounded-3xl bg-surface-100 dark:bg-surface-900" />
          <div className="h-[520px] rounded-3xl bg-surface-100 dark:bg-surface-900" />
        </div>
      }
    >
      <LoginForm />
    </Suspense>
  );
}
