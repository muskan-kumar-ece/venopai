/**
 * Button Component
 * 
 * A versatile button component with multiple variants, sizes, and states.
 * Follows the VenoPai design system principles for ecommerce UX.
 */

import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "tap-highlight-none inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium transition-[background-color,border-color,color,box-shadow,transform,opacity] motion-standard motion-safe:hover:-translate-y-0.5 motion-safe:active:translate-y-0 motion-safe:active:scale-[0.985] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ring-offset-background disabled:pointer-events-none disabled:translate-y-0 disabled:scale-100 disabled:opacity-50",
  {
    variants: {
      variant: {
        primary: [
          "bg-primary-600 text-white hover:bg-primary-700 active:bg-primary-800",
          "focus-visible:ring-primary-500",
          "disabled:bg-primary-400",
        ],
        secondary: [
          "bg-surface-100 text-surface-900 border border-surface-300 hover:bg-surface-200",
          "dark:bg-surface-800 dark:text-surface-100 dark:border-surface-700 dark:hover:bg-surface-700",
        ],
        ghost: [
          "bg-transparent text-surface-900 hover:bg-surface-100",
          "dark:text-surface-100 dark:hover:bg-surface-800",
        ],
        destructive: [
          "bg-error-600 text-white hover:bg-error-700 active:bg-error-800",
          "focus-visible:ring-error-500",
          "disabled:bg-error-400",
        ],
        danger: [
          "bg-error-600 text-white hover:bg-error-700 active:bg-error-800",
          "focus-visible:ring-error-500",
          "disabled:bg-error-400",
        ],
        commerce: [
          "bg-cta-primary text-white hover:bg-primary-700 active:bg-primary-800",
          "focus-visible:ring-primary-500",
          "disabled:bg-primary-400",
        ],
        outline: [
          "border border-primary-500 text-primary-600 hover:bg-primary-50 dark:hover:bg-primary-900/20",
        ],
      },
      size: {
        xs: "h-7 px-2.5 text-xs",
        sm: "h-9 px-3 text-sm",
        md: "h-11 px-4 text-sm",
        lg: "h-[52px] px-6 text-base",
        icon: "h-10 w-10 p-0",
      },
      state: {
        loading: "relative",
        default: "",
      },
    },
    defaultVariants: {
      variant: "primary",
      size: "md",
      state: "default",
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
  loading?: boolean;
  iconLeft?: React.ReactNode;
  iconRight?: React.ReactNode;
  fullWidth?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant,
      size,
      fullWidth,
      asChild = false,
      loading = false,
      iconLeft,
      iconRight,
      disabled,
      children,
      ...props
    },
    ref
  ) => {
    const baseClasses = cn(buttonVariants({ variant, size, className, state: loading ? "loading" : "default" }));
    
    if (fullWidth) {
      return (
        <button
          type="button"
          className={cn(baseClasses, "w-full")}
          ref={ref}
          disabled={disabled || loading}
          {...props}
        >
          {loading && (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
          )}
          {!loading && iconLeft && <span className="mr-2">{iconLeft}</span>}
          {children}
          {!loading && iconRight && <span className="ml-2">{iconRight}</span>}
        </button>
      );
    }

    if (asChild) {
      return (
        <Slot
          className={baseClasses}
          ref={ref}
          {...props}
        >
          {children}
        </Slot>
      );
    }

    return (
      <button
        type="button"
        className={baseClasses}
        ref={ref}
        disabled={disabled || loading}
        {...props}
      >
        {loading && (
          <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
        )}
        {!loading && iconLeft && <span className="mr-2">{iconLeft}</span>}
        {children}
        {!loading && iconRight && <span className="ml-2">{iconRight}</span>}
      </button>
    );
  }
);
Button.displayName = "Button";

export { Button, buttonVariants };
