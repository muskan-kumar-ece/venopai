"use client";

import { useEffect } from "react";

export function ObservabilityProvider({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    const dsn = process.env.NEXT_PUBLIC_SENTRY_DSN;
    if (!dsn) {
      return;
    }
    void import("@sentry/nextjs").then((Sentry) => {
      Sentry.init({
        dsn,
        environment: process.env.NEXT_PUBLIC_ENVIRONMENT ?? "dev",
        tracesSampleRate: 0,
      });
      if (typeof window !== "undefined") {
        window.Sentry = {
          captureException: (error, ctx) => {
            Sentry.captureException(error, ctx as Parameters<typeof Sentry.captureException>[1]);
          },
          captureMessage: (message, ctx) => {
            Sentry.captureMessage(message, ctx as Parameters<typeof Sentry.captureMessage>[1]);
          },
        };
      }
    });
  }, []);

  return <>{children}</>;
}
