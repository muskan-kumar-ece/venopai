/**
 * Card Component
 * 
 * A versatile card component with multiple variants for different content types.
 * Follows the VenoPai design system principles for ecommerce UX.
 */

import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const cardVariants = cva(
  "rounded-lg transition-[border-color,background-color,box-shadow,transform] motion-standard motion-safe:hover:-translate-y-0.5",
  {
    variants: {
      variant: {
        product: [
          "border border-surface-200 bg-surface-50 shadow-sm hover:shadow-md",
          "dark:border-surface-700 dark:bg-surface-900",
        ],
        category: [
          "border border-surface-200 bg-surface-100 shadow-sm hover:shadow-md",
          "dark:border-surface-700 dark:bg-surface-800",
        ],
        feature: [
          "border border-surface-200 bg-surface-100 shadow-sm hover:shadow-md",
          "dark:border-surface-700 dark:bg-surface-800",
        ],
        elevated: [
          "border border-surface-200 bg-surface-50 shadow-md hover:shadow-lg",
          "dark:border-surface-700 dark:bg-surface-900",
        ],
        flat: [
          "border border-transparent bg-surface-50 hover:bg-surface-100",
          "dark:bg-surface-800 dark:hover:bg-surface-700",
        ],
        interactive: [
          "border border-surface-200 bg-surface-50 shadow-sm hover:shadow-md cursor-pointer",
          "dark:border-surface-700 dark:bg-surface-900",
        ],
      },
      size: {
        sm: "p-3",
        md: "p-4",
        lg: "p-6",
      },
    },
    defaultVariants: {
      variant: "product",
      size: "md",
    },
  }
);

export interface CardProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof cardVariants> {
  header?: React.ReactNode;
  footer?: React.ReactNode;
}

const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ className, variant, size, header, footer, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(cardVariants({ variant, size, className }))}
      {...props}
    >
      {header && <div className="flex items-center justify-between">{header}</div>}
      <div className="mt-2">{props.children}</div>
      {footer && <div className="mt-3 flex items-center justify-between">{footer}</div>}
    </div>
  )
);
Card.displayName = "Card";

const CardHeader = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("flex flex-col space-y-1.5 p-0", className)}
    {...props}
  />
));
CardHeader.displayName = "CardHeader";

const CardTitle = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLHeadingElement>
>(({ className, ...props }, ref) => (
  <h3
    ref={ref}
    className={cn(
      "text-lg font-semibold tracking-tight text-surface-900 dark:text-surface-50",
      className
    )}
    {...props}
  />
));
CardTitle.displayName = "CardTitle";

const CardDescription = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLParagraphElement>
>(({ className, ...props }, ref) => (
  <p
    ref={ref}
    className={cn("text-sm text-surface-500 dark:text-surface-400", className)}
    {...props}
  />
));
CardDescription.displayName = "CardDescription";

const CardContent = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div ref={ref} className={cn("p-0", className)} {...props} />
));
CardContent.displayName = "CardContent";

const CardFooter = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div ref={ref} className={cn("flex items-center justify-between p-0", className)} {...props} />
));
CardFooter.displayName = "CardFooter";

export { 
  Card, 
  CardHeader, 
  CardTitle, 
  CardDescription, 
  CardContent, 
  CardFooter, 
  cardVariants 
};
