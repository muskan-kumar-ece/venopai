/**
 * Radio Component
 * 
 * A versatile radio button component with multiple variants and states.
 * Follows the VenoPai design system principles for ecommerce UX.
 */

import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const radioVariants = cva(
  "h-4 w-4 shrink-0 cursor-pointer rounded-full border border-primary text-primary-600 accent-primary-600 ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50",
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
      },
    },
    defaultVariants: {
      variant: "default",
      size: "md",
      state: "unchecked",
    },
  }
);

export interface RadioProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "size" | "type"> {
  variant?: VariantProps<typeof radioVariants>["variant"];
  size?: VariantProps<typeof radioVariants>["size"];
  state?: VariantProps<typeof radioVariants>["state"];
  children?: React.ReactNode;
}

const Radio = React.forwardRef<HTMLInputElement, RadioProps>(
  ({ className, variant, size, state, children, id, ...props }, ref) => {
    return (
      <div className={cn("flex items-center", className)}>
        <input
          ref={ref}
          id={id}
          type="radio"
          className={cn(radioVariants({ variant, size, state }))}
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
Radio.displayName = "Radio";

export { Radio, radioVariants };
