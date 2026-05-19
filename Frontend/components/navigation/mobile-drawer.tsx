import * as React from "react";
import Link from "next/link";
import { LogIn, Menu, ShieldCheck, Truck, UserRound } from "lucide-react";

import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

interface MobileDrawerProps {
  className?: string;
  children?: React.ReactNode;
  links?: Array<{
    href: string;
    label: string;
    icon?: React.ComponentType<{ className?: string; "aria-hidden"?: boolean | "true" | "false" }>;
  }>;
  signedIn?: boolean;
}

const MobileDrawer = React.forwardRef<HTMLDivElement, MobileDrawerProps>(
  ({ className, children, links = [], signedIn = false, ...props }, ref) => {
    return (
      <Sheet>
        <SheetTrigger asChild>
          <Button
            variant="ghost"
            size="icon"
            className="rounded-full bg-surface-100 text-surface-800 hover:bg-primary-50 hover:text-primary-700 dark:bg-surface-800 dark:text-surface-100 lg:hidden"
          >
            <Menu className="h-5 w-5" aria-hidden="true" />
            <span className="sr-only">Toggle menu</span>
          </Button>
        </SheetTrigger>
        <SheetContent side="left" className="w-[min(88vw,360px)] p-0" ref={ref} {...props}>
          <div className={cn("flex min-h-full flex-col", className)}>
            <div className="border-b border-surface-200 bg-surface-50 px-5 py-5 dark:border-surface-800 dark:bg-surface-900">
              <Link
                href="/"
                className="inline-flex items-center gap-2 rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2"
              >
                <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary-600 text-sm font-black text-white shadow-sm shadow-primary-600/25">
                  V
                </span>
                <span className="text-lg font-bold tracking-tight text-surface-900 dark:text-surface-50">VenoPai</span>
              </Link>
              <div className="mt-4 grid gap-2 text-xs font-medium text-surface-600 dark:text-surface-300">
                <span className="inline-flex items-center gap-2">
                  <ShieldCheck className="h-4 w-4 text-success-600" aria-hidden="true" />
                  Secure shopping
                </span>
                <span className="inline-flex items-center gap-2">
                  <Truck className="h-4 w-4 text-primary-600" aria-hidden="true" />
                  Reliable delivery support
                </span>
              </div>
            </div>

            <nav aria-label="Mobile navigation" className="grid gap-1 p-3">
              {links.map((link) => {
                const Icon = link.icon;
                return (
                  <Link
                    key={link.href}
                    href={link.href}
                    className="flex min-h-12 items-center gap-3 rounded-xl px-3 text-sm font-semibold text-surface-700 transition-colors hover:bg-surface-100 hover:text-surface-950 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2 dark:text-surface-200 dark:hover:bg-surface-800 dark:hover:text-white"
                  >
                    {Icon ? <Icon className="h-4 w-4 text-primary-600" aria-hidden="true" /> : null}
                    {link.label}
                  </Link>
                );
              })}
            </nav>

            <div className="mt-auto border-t border-surface-200 p-4 pb-[calc(1rem+env(safe-area-inset-bottom))] dark:border-surface-800">
              <Button asChild variant={signedIn ? "secondary" : "primary"} className="w-full rounded-full">
                <Link href={signedIn ? "/account/orders" : "/login"}>
                  {signedIn ? (
                    <UserRound className="mr-2 h-4 w-4" aria-hidden="true" />
                  ) : (
                    <LogIn className="mr-2 h-4 w-4" aria-hidden="true" />
                  )}
                  {signedIn ? "My account" : "Sign in"}
                </Link>
              </Button>
              {children}
            </div>
          </div>
        </SheetContent>
      </Sheet>
    );
  }
);
MobileDrawer.displayName = "MobileDrawer";

export { MobileDrawer };
