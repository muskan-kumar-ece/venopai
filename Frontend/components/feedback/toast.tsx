"use client";

import * as React from "react";
import { AlertCircle, CheckCircle2, Info, X } from "lucide-react";

import { cn } from "@/lib/utils";

type FeedbackToastVariant = "default" | "success" | "error" | "warning";

const variantClasses: Record<FeedbackToastVariant, string> = {
  default: "border-primary-200 bg-primary-50 text-primary-900 dark:border-primary-800/40 dark:bg-primary-900/20 dark:text-primary-200",
  success: "border-success-200 bg-success-50 text-success-900 dark:border-success-800/40 dark:bg-success-900/20 dark:text-success-200",
  error: "border-error-200 bg-error-50 text-error-900 dark:border-error-800/40 dark:bg-error-900/20 dark:text-error-200",
  warning: "border-warning-200 bg-warning-50 text-warning-900 dark:border-warning-800/40 dark:bg-warning-900/20 dark:text-warning-200",
};

const Toast = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement> & {
    title?: string;
    description?: string;
    variant?: FeedbackToastVariant;
    onClose?: () => void;
  }
>(({ className, title, description, variant = "default", onClose, ...props }, ref) => {
  const Icon = variant === "success" ? CheckCircle2 : variant === "error" || variant === "warning" ? AlertCircle : Info;

  return (
    <div
      ref={ref}
      role={variant === "error" || variant === "warning" ? "alert" : "status"}
      className={cn(
        "relative flex w-[min(100%,380px)] items-start gap-3 rounded-2xl border p-4 pr-10 text-sm shadow-xl shadow-surface-900/10 backdrop-blur transition-[opacity,transform] motion-slow",
        variantClasses[variant],
        className,
      )}
      {...props}
    >
      <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-white/70 dark:bg-surface-950/40">
        <Icon className="h-4 w-4" aria-hidden="true" />
      </div>
      <div className="min-w-0 flex-1 space-y-1">
        {title ? <p className="font-bold leading-none">{title}</p> : null}
        {description ? <p className="leading-5 opacity-90">{description}</p> : null}
      </div>
      {onClose ? (
        <button
          type="button"
          onClick={onClose}
          className="absolute right-3 top-3 rounded-full p-1 opacity-70 transition-opacity motion-standard hover:opacity-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-current focus-visible:ring-offset-2"
          aria-label="Close toast"
        >
          <X className="h-4 w-4" aria-hidden="true" />
        </button>
      ) : null}
    </div>
  );
});
Toast.displayName = "Toast";

export { Toast };
