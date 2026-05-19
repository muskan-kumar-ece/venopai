"use client";

import * as React from "react";
import { AlertCircle, CheckCircle2, Info, Loader2, X } from "lucide-react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const toastVariants = cva(
  "flex items-start gap-3 opacity-0 translate-y-2 sm:translate-x-4 sm:translate-y-0 motion-safe:transition-[opacity,transform] motion-slow",
  {
    variants: {
      variant: {
        success:
          "border-green-200 bg-green-50 text-green-800 dark:border-green-800/40 dark:bg-green-900/20 dark:text-green-300",
        error:
          "border-red-200 bg-red-50 text-red-800 dark:border-red-800/40 dark:bg-red-900/20 dark:text-red-300",
        warning:
          "border-yellow-200 bg-yellow-50 text-yellow-800 dark:border-yellow-800/40 dark:bg-yellow-900/20 dark:text-yellow-300",
        info: "border-primary-200 bg-primary-50 text-primary-800 dark:border-primary-800/40 dark:bg-primary-900/20 dark:text-primary-300",
      },
    },
    defaultVariants: {
      variant: "info",
    },
  },
);

export interface ToastProps
  extends Omit<React.HTMLAttributes<HTMLDivElement>, "title">,
    VariantProps<typeof toastVariants> {
  title?: React.ReactNode;
  description?: React.ReactNode;
  onClose?: () => void;
  exiting?: boolean;
}

const Toast = React.forwardRef<HTMLDivElement, ToastProps>(
  ({ className, variant, title, description, onClose, exiting, ...props }, ref) => {
    const [isVisible, setIsVisible] = React.useState(false);

    React.useEffect(() => {
      const frameId = window.requestAnimationFrame(() => setIsVisible(true));
      return () => window.cancelAnimationFrame(frameId);
    }, []);

    const Icon =
      variant === "success" ? CheckCircle2 : variant === "error" ? AlertCircle : variant === "warning" ? AlertCircle : Info;

    return (
      <div
        ref={ref}
        role={variant === "error" || variant === "warning" ? "alert" : "status"}
        className={cn(
          toastVariants({ variant }),
          "w-[min(calc(100vw-2rem),380px)] rounded-2xl border p-4 shadow-xl shadow-surface-900/10 backdrop-blur",
          exiting ? "translate-y-2 opacity-0 sm:translate-x-4 sm:translate-y-0" : isVisible && "translate-x-0 translate-y-0 opacity-100",
          className,
        )}
        {...props}
      >
        <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-white/70 dark:bg-surface-950/40">
          {title === "Loading" ? <Loader2 className="h-4 w-4 motion-safe:animate-spin" aria-hidden="true" /> : <Icon className="h-4 w-4" aria-hidden="true" />}
        </div>
        <div className="flex-1 space-y-1">
          {title ? <p className="font-medium leading-none">{title}</p> : null}
          {description ? <p className="text-sm opacity-90">{description}</p> : null}
        </div>
        <button
          type="button"
          aria-label="Close toast"
          className="rounded-sm opacity-70 transition-opacity motion-standard hover:opacity-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-current focus-visible:ring-offset-2 ring-offset-background"
          onClick={onClose}
        >
          <X className="h-4 w-4" />
        </button>
      </div>
    );
  },
);
Toast.displayName = "Toast";

export { Toast, toastVariants };
