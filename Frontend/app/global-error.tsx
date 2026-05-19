"use client";

import { useEffect } from "react";

import { captureClientError } from "@/lib/observability";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    captureClientError(error, { digest: error.digest, scope: "global" });
  }, [error]);

  return (
    <html lang="en">
      <body className="min-h-dvh bg-neutral-50 text-neutral-900">
        <main className="mx-auto flex min-h-dvh max-w-xl flex-col items-center justify-center gap-4 p-6 text-center">
          <div role="alert" className="rounded-3xl border border-error-200 bg-white p-6 shadow-sm">
            <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-3xl bg-error-50 text-error-600">
              !
            </div>
            <h1 className="mt-5 text-2xl font-black tracking-tight">Something went wrong</h1>
            <p className="mt-3 text-sm leading-6 text-neutral-600">We logged this issue. Please retry the action.</p>
            <button
              type="button"
              onClick={reset}
              className="mt-6 inline-flex h-11 items-center justify-center rounded-full bg-primary-600 px-5 text-sm font-semibold text-white transition-colors hover:bg-primary-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2"
            >
              Retry
            </button>
          </div>
        </main>
      </body>
    </html>
  );
}
