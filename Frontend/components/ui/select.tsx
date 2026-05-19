/**
 * Select Component
 * 
 * A versatile select component with multiple variants and states.
 * Follows the VenoPai design system principles for ecommerce UX.
 */

import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";
import { ChevronDown } from "lucide-react";

const selectVariants = cva(
  "flex h-10 w-full items-center justify-between rounded-md border border-input bg-transparent px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50",
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

export interface SelectProps
  extends Omit<React.SelectHTMLAttributes<HTMLSelectElement>, "size"> {
  variant?: VariantProps<typeof selectVariants>["variant"];
  size?: VariantProps<typeof selectVariants>["size"];
  state?: VariantProps<typeof selectVariants>["state"];
}

const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, variant, size, state, children, ...props }, ref) => {
    const baseClasses = cn(selectVariants({ variant, size, state, className }));
    
    return (
      <div className="relative">
        <select
          ref={ref}
          className={cn(baseClasses)}
          {...props}
        >
          {children}
        </select>
        <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none">
          <ChevronDown className="h-4 w-4 text-muted-foreground" />
        </div>
      </div>
    );
  }
);
Select.displayName = "Select";

export { Select, selectVariants };
