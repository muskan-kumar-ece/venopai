/**
 * Input Component
 * 
 * A versatile input component with multiple variants and states.
 * Follows the VenoPai design system principles for ecommerce UX.
 */

import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const inputVariants = cva(
  "tap-highlight-none flex h-10 w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm ring-offset-background transition-[border-color,background-color,box-shadow,color,opacity] motion-standard file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "border-surface-300 focus-visible:ring-primary-500 dark:border-surface-700",
        outlined: "border-surface-200 focus-visible:ring-primary-500 dark:border-surface-700",
        filled: "bg-surface-100 border-transparent focus-visible:ring-primary-500 dark:bg-surface-800",
      },
      size: {
        sm: "h-8",
        md: "h-10",
        lg: "h-12",
      },
      state: {
        error: "border-error-500 text-error-600 focus-visible:ring-error-500 dark:text-error-400",
        success: "border-success-500 text-success-600 focus-visible:ring-success-500 dark:text-success-400",
        warning: "border-warning-500 text-warning-600 focus-visible:ring-warning-500 dark:text-warning-400",
        default: "",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "md",
      state: "default",
    },
  }
);

export interface InputProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "size">,
    VariantProps<typeof inputVariants> {
  icon?: React.ReactNode;
  iconPosition?: "left" | "right";
}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, variant, size, state, icon, iconPosition = "left", ...props }, ref) => {
    const baseClasses = cn(inputVariants({ variant, size, state, className }));
    
    return (
      <div className="relative">
        {icon && iconPosition === "left" && (
          <div className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">
            {icon}
          </div>
        )}
        <input
          ref={ref}
          className={cn(baseClasses, 
            icon && iconPosition === "left" ? "pl-10" : "",
            icon && iconPosition === "right" ? "pr-10" : ""
          )}
          {...props}
        />
        {icon && iconPosition === "right" && (
          <div className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground">
            {icon}
          </div>
        )}
      </div>
    );
  }
);
Input.displayName = "Input";

export { Input, inputVariants };
