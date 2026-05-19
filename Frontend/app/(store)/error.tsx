"use client";

import { useEffect } from "react";

import { ErrorState } from "@/components/feedback/error-state";
import { captureClientError } from "@/lib/observability";

export default function StoreError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    captureClientError(error, { digest: error.digest, scope: "storefront" });
  }, [error]);

  return (
    <ErrorState
      title="Storefront temporarily unavailable"
      description="Try again. If this keeps happening, support can use your request logs."
      onRetry={reset}
      className="mx-auto my-16 max-w-xl"
    />
  );
}
