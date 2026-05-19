/**
 * Form Group Component
 * 
 * A reusable form group component that wraps label and input elements.
 * Follows the VenoPai design system principles for ecommerce UX.
 */

import * as React from "react";
import { cn } from "@/lib/utils";

export interface FormGroupProps {
  label?: React.ReactNode;
  required?: boolean;
  children: React.ReactNode;
  className?: string;
}

const FormGroup = React.forwardRef<HTMLDivElement, FormGroupProps>(
  ({ label, required, children, className, ...props }, ref) => {
    return (
      <div ref={ref} className={cn("space-y-2", className)} {...props}>
        {label && (
          <label className="text-sm font-medium leading-none">
            {label}
            {required && <span className="text-error-500">*</span>}
          </label>
        )}
        {children}
      </div>
    );
  }
);
FormGroup.displayName = "FormGroup";

export { FormGroup };