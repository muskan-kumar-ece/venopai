/**
 * Textarea Component
 * 
 * A versatile textarea component with multiple variants and states.
 * Follows the VenoPai design system principles for ecommerce UX.
 */

import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const textareaVariants = cva(
  "tap-highlight-none flex w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm ring-offset-background transition-[border-color,background-color,box-shadow,color,opacity] motion-standard placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "border-surface-300 focus-visible:ring-primary-500 dark:border-surface-700",
        outlined: "border-surface-200 focus-visible:ring-primary-500 dark:border-surface-700",
        filled: "bg-surface-100 border-transparent focus-visible:ring-primary-500 dark:bg-surface-800",
      },
      size: {
        sm: "h-8 resize-none",
        md: "h-10 resize-none",
        lg: "h-12 resize-none",
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

export interface TextareaProps
  extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  variant?: VariantProps<typeof textareaVariants>["variant"];
  size?: VariantProps<typeof textareaVariants>["size"];
  state?: VariantProps<typeof textareaVariants>["state"];
}

const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, variant, size, state, children, ...props }, ref) => {
    const baseClasses = cn(textareaVariants({ variant, size, state, className }));
    
    return (
      <textarea
        ref={ref}
        className={baseClasses}
        {...props}
      >
        {children}
      </textarea>
    );
  }
);
Textarea.displayName = "Textarea";

export { Textarea, textareaVariants };
