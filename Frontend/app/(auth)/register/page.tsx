"use client";

import Link from "next/link";
import {
  ArrowLeft,
  BadgeCheck,
  Clock3,
  LockKeyhole,
  MailCheck,
  ShieldCheck,
  ShoppingBag,
  UserPlus,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

const accountNotes = [
  { icon: LockKeyhole, title: "Access stays controlled", copy: "New accounts are not opened from the storefront in the current auth contract." },
  { icon: ShieldCheck, title: "Secure sign in remains active", copy: "Existing users can continue using the protected JWT sign-in flow." },
  { icon: ShoppingBag, title: "Commerce context is preserved", copy: "Cart, checkout, wishlist, and order access continue through signed-in sessions." },
];

export default function RegisterPage() {
  return (
    <section className="mx-auto grid w-full max-w-6xl gap-6 px-4 py-6 sm:px-6 sm:py-8 lg:grid-cols-[minmax(0,1fr)_430px] lg:items-center lg:px-8 lg:py-12">
      <div className="rounded-3xl border border-surface-200 bg-white p-5 shadow-sm dark:border-surface-800 dark:bg-surface-900 sm:p-7">
        <Link
          href="/login"
          className="inline-flex items-center gap-2 rounded-full bg-surface-100 px-3 py-2 text-sm font-semibold text-surface-700 transition-colors hover:bg-primary-50 hover:text-primary-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2 dark:bg-surface-800 dark:text-surface-200 dark:hover:bg-primary-900/30"
        >
          <ArrowLeft className="h-4 w-4" aria-hidden="true" />
          Back to sign in
        </Link>

        <div className="mt-8 max-w-2xl">
          <p className="text-sm font-semibold uppercase tracking-wide text-primary-700 dark:text-primary-300">
            Account access
          </p>
          <h1 className="mt-3 text-3xl font-black tracking-tight text-surface-950 dark:text-white sm:text-4xl lg:text-5xl">
            Account creation is currently invite-managed.
          </h1>
          <p className="mt-4 text-sm leading-6 text-surface-600 dark:text-surface-300 sm:text-base">
            VenoPai is keeping storefront registration closed while existing account sign-in remains available for shopping, checkout, and order tracking.
          </p>
        </div>

        <div className="mt-8 grid gap-3">
          {accountNotes.map((item) => {
            const Icon = item.icon;
            return (
              <div key={item.title} className="rounded-2xl bg-surface-50 p-4 dark:bg-surface-950">
                <div className="flex items-start gap-3">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-primary-50 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300">
                    <Icon className="h-5 w-5" aria-hidden="true" />
                  </div>
                  <div>
                    <p className="text-sm font-black text-surface-950 dark:text-white">{item.title}</p>
                    <p className="mt-1 text-sm leading-6 text-surface-500 dark:text-surface-400">{item.copy}</p>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <Card className="rounded-3xl border-surface-200 bg-white p-5 shadow-xl shadow-surface-900/5 dark:border-surface-800 dark:bg-surface-900 sm:p-6">
        <CardContent className="space-y-6">
          <div className="flex h-14 w-14 items-center justify-center rounded-3xl bg-primary-50 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300">
            <UserPlus className="h-7 w-7" aria-hidden="true" />
          </div>

          <div>
            <h2 className="text-2xl font-black tracking-tight text-surface-950 dark:text-white">Registration unavailable</h2>
            <p className="mt-2 text-sm leading-6 text-surface-500 dark:text-surface-400">
              Signup is not exposed in the current API contract. Authorized users should sign in with existing credentials.
            </p>
          </div>

          <div className="grid gap-3 rounded-3xl bg-surface-50 p-4 dark:bg-surface-950">
            <div className="flex items-start gap-3 text-sm leading-6 text-surface-600 dark:text-surface-300">
              <MailCheck className="mt-0.5 h-4 w-4 shrink-0 text-success-600" aria-hidden="true" />
              <span>Account access is managed outside the storefront registration page.</span>
            </div>
            <div className="flex items-start gap-3 text-sm leading-6 text-surface-600 dark:text-surface-300">
              <BadgeCheck className="mt-0.5 h-4 w-4 shrink-0 text-primary-600" aria-hidden="true" />
              <span>Existing sign-in keeps account and order access protected.</span>
            </div>
            <div className="flex items-start gap-3 text-sm leading-6 text-surface-600 dark:text-surface-300">
              <Clock3 className="mt-0.5 h-4 w-4 shrink-0 text-warning-600" aria-hidden="true" />
              <span>Try again only after receiving account access from the VenoPai team.</span>
            </div>
          </div>

          <Button asChild size="lg" fullWidth className="rounded-full">
            <Link href="/login">Go to secure sign in</Link>
          </Button>
          <Button type="button" variant="secondary" size="lg" fullWidth disabled className="rounded-full">
            Create account unavailable
          </Button>
        </CardContent>
      </Card>
    </section>
  );
}
