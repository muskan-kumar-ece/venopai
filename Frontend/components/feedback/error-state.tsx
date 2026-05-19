import type * as React from "react";
import { AlertCircle, RotateCcw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface ErrorStateProps {
  title: string;
  description?: string;
  action?: React.ReactNode;
  onRetry?: () => void;
  retryLabel?: string;
  isRetrying?: boolean;
  className?: string;
}

const ErrorState = ({ title, description, action, onRetry, retryLabel = "Retry", isRetrying, className }: ErrorStateProps) => {
  return (
    <section
      role="alert"
      className={cn(
        "rounded-3xl border border-error-200 bg-error-50/80 p-6 text-center shadow-sm dark:border-error-900/50 dark:bg-error-900/20 sm:p-8",
        className,
      )}
    >
      <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-3xl bg-white text-error-600 shadow-sm dark:bg-error-950/40 dark:text-error-300">
        <AlertCircle className="h-7 w-7" aria-hidden="true" />
      </div>
      <h2 className="mt-5 text-2xl font-black tracking-tight text-error-900 dark:text-error-100">{title}</h2>
      {description ? (
        <p className="mx-auto mt-3 max-w-md text-sm leading-6 text-error-700 dark:text-error-200">{description}</p>
      ) : null}
      {onRetry || action ? (
        <div className="mt-6 flex flex-col justify-center gap-3 sm:flex-row">
          {onRetry ? (
            <Button
              type="button"
              variant="secondary"
              className="rounded-full"
              onClick={onRetry}
              loading={isRetrying}
              iconLeft={<RotateCcw className="h-4 w-4" aria-hidden="true" />}
            >
              {isRetrying ? "Retrying..." : retryLabel}
            </Button>
          ) : null}
          {action}
        </div>
      ) : null}
    </section>
  );
};

export { ErrorState };
