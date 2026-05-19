/**
 * Checkbox Component
 * 
 * A versatile checkbox component with multiple variants and states.
 * Follows the VenoPai design system principles for ecommerce UX.
 */

import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const checkboxVariants = cva(
  "h-4 w-4 shrink-0 cursor-pointer rounded-sm border border-primary text-primary-600 accent-primary-600 ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "border-surface-300",
        outlined: "border-surface-200",
      },
      size: {
        sm: "h-3 w-3",
        md: "h-4 w-4",
        lg: "h-5 w-5",
      },
      state: {
        checked: "",
        unchecked: "",
        indeterminate: "",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "md",
      state: "unchecked",
    },
  }
);

export interface CheckboxProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "size" | "type"> {
  variant?: VariantProps<typeof checkboxVariants>["variant"];
  size?: VariantProps<typeof checkboxVariants>["size"];
  state?: VariantProps<typeof checkboxVariants>["state"];
}

const Checkbox = React.forwardRef<HTMLInputElement, CheckboxProps>(
  ({ className, variant, size, state, children, id, ...props }, ref) => {
    return (
      <div className={cn("flex items-center", className)}>
        <input
          ref={ref}
          id={id}
          type="checkbox"
          className={cn(checkboxVariants({ variant, size, state }))}
          {...props}
        />
        {children && (
          <label htmlFor={id} className="ml-2 text-sm font-medium leading-none">
            {children}
          </label>
        )}
      </div>
    );
  }
);
Checkbox.displayName = "Checkbox";

export { Checkbox, checkboxVariants };
