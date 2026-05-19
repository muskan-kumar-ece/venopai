import type * as React from "react";
import { ShoppingBag } from "lucide-react";

import { cn } from "@/lib/utils";

interface EmptyStateProps {
  title: string;
  description?: string;
  icon?: React.ReactNode;
  action?: React.ReactNode;
  secondaryAction?: React.ReactNode;
  eyebrow?: string;
  className?: string;
}

const EmptyState = ({ title, description, icon, action, secondaryAction, eyebrow, className }: EmptyStateProps) => {
  return (
    <section
      className={cn(
        "rounded-3xl border border-dashed border-surface-300 bg-white p-6 text-center shadow-sm dark:border-surface-700 dark:bg-surface-900 sm:p-8",
        className,
      )}
    >
      <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-3xl bg-primary-50 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300">
        {icon ?? <ShoppingBag className="h-7 w-7" aria-hidden="true" />}
      </div>
      {eyebrow ? (
        <p className="mt-5 text-xs font-bold uppercase tracking-wide text-primary-700 dark:text-primary-300">{eyebrow}</p>
      ) : null}
      <h2 className="mt-3 text-2xl font-black tracking-tight text-surface-950 dark:text-white">{title}</h2>
      {description ? (
        <p className="mx-auto mt-3 max-w-md text-sm leading-6 text-surface-500 dark:text-surface-300">{description}</p>
      ) : null}
      {action || secondaryAction ? (
        <div className="mt-6 flex flex-col justify-center gap-3 sm:flex-row">
          {action}
          {secondaryAction}
        </div>
      ) : null}
    </section>
  );
};

export { EmptyState };
