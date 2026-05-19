import type * as React from "react";
import { CheckCircle2 } from "lucide-react";

import { cn } from "@/lib/utils";

interface SuccessStateProps {
  title: string;
  description?: string;
  action?: React.ReactNode;
  icon?: React.ReactNode;
  className?: string;
}

const SuccessState = ({ title, description, action, icon, className }: SuccessStateProps) => {
  return (
    <section
      role="status"
      className={cn(
        "rounded-3xl border border-success-200 bg-success-50/80 p-6 text-center shadow-sm dark:border-success-900/50 dark:bg-success-900/20 sm:p-8",
        className,
      )}
    >
      <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-3xl bg-white text-success-700 shadow-sm dark:bg-success-950/40 dark:text-success-300">
        {icon ?? <CheckCircle2 className="h-7 w-7" aria-hidden="true" />}
      </div>
      <h2 className="mt-5 text-2xl font-black tracking-tight text-success-950 dark:text-success-100">{title}</h2>
      {description ? (
        <p className="mx-auto mt-3 max-w-md text-sm leading-6 text-success-700 dark:text-success-200">{description}</p>
      ) : null}
      {action ? <div className="mt-6 flex justify-center">{action}</div> : null}
    </section>
  );
};

export { SuccessState };
