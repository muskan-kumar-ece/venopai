"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Heart,
  Home,
  LogIn,
  PackageSearch,
  Search,
  ShieldCheck,
  ShoppingCart,
  Sparkles,
  Truck,
  UserRound,
} from "lucide-react";

import { useAuth } from "@/components/providers/auth-provider";
import { useCartUI } from "@/components/providers/cart-context";
import { useCart } from "@/lib/cart/use-cart";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { MobileDrawer } from "@/components/navigation/mobile-drawer";

interface NavbarProps {
  className?: string;
}

const primaryLinks = [
  { href: "/", label: "Home", icon: Home },
  { href: "/products", label: "Products", icon: PackageSearch },
  { href: "/wishlist", label: "Wishlist", icon: Heart },
  { href: "/referral", label: "Rewards", icon: Sparkles },
];

const Navbar = React.forwardRef<HTMLDivElement, NavbarProps>(
  ({ className, ...props }, ref) => {
    const router = useRouter();
    const { accessToken, isReady } = useAuth();
    const { openDrawer } = useCartUI();
    const { itemCount, isFetching } = useCart();
    const [search, setSearch] = React.useState("");
    const isSignedIn = Boolean(accessToken);

    const submitSearch = (event: React.FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      const query = search.trim();
      router.push(query ? `/products?q=${encodeURIComponent(query)}` : "/products");
    };

    return (
      <header className={cn("sticky top-0 z-40 border-b border-surface-200/80 bg-white/95 pt-safe shadow-sm backdrop-blur-xl dark:border-surface-800 dark:bg-neutral-950/90", className)}>
        <div className="hidden border-b border-surface-200/70 bg-surface-50/80 dark:border-surface-800 dark:bg-surface-900/70 lg:block">
          <div className="mx-auto flex h-9 max-w-[1280px] items-center justify-between px-4 text-xs font-medium text-surface-600 dark:text-surface-300 sm:px-6 lg:px-8">
            <div className="flex items-center gap-5">
              <span className="inline-flex items-center gap-1.5">
                <ShieldCheck className="h-3.5 w-3.5 text-success-600" aria-hidden="true" />
                Secure checkout
              </span>
              <span className="inline-flex items-center gap-1.5">
                <Truck className="h-3.5 w-3.5 text-primary-600" aria-hidden="true" />
                Reliable delivery
              </span>
            </div>
            <Link href="/referral" className="text-primary-700 transition-colors hover:text-primary-800 dark:text-primary-300 dark:hover:text-primary-200">
              Earn rewards on every referral
            </Link>
          </div>
        </div>

        <div ref={ref} className="mx-auto max-w-[1280px] px-4 sm:px-6 lg:px-8" {...props}>
          <div className="flex min-h-16 flex-wrap items-center gap-3 py-3 lg:flex-nowrap lg:gap-5">
            <MobileDrawer links={primaryLinks} signedIn={isSignedIn} />

            <Link href="/" className="group flex shrink-0 items-center gap-2 rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2">
              <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary-600 text-sm font-black text-white shadow-sm shadow-primary-600/25 transition-transform group-hover:scale-[1.03]">
                V
              </span>
              <span className="hidden text-lg font-bold tracking-tight text-surface-900 dark:text-surface-50 sm:block">
                VenoPai
              </span>
            </Link>

            <nav aria-label="Primary navigation" className="hidden items-center gap-1 lg:flex">
              {primaryLinks.map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  className="rounded-full px-3 py-2 text-sm font-medium text-surface-600 transition-colors hover:bg-surface-100 hover:text-surface-950 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2 dark:text-surface-300 dark:hover:bg-surface-800 dark:hover:text-white"
                >
                  {link.label}
                </Link>
              ))}
            </nav>

            <form onSubmit={submitSearch} role="search" className="order-last w-full min-w-0 lg:order-none lg:flex-1">
              <label htmlFor="site-search" className="sr-only">
                Search products
              </label>
              <div className="group relative">
                <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-surface-400 transition-colors group-focus-within:text-primary-600" aria-hidden="true" />
                <input
                  id="site-search"
                  type="search"
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder="Search products..."
                  className="h-11 w-full rounded-full border border-surface-300 bg-surface-50 pl-10 pr-4 text-sm text-surface-900 shadow-inner outline-none transition-all placeholder:text-surface-500 focus:border-primary-500 focus:bg-white focus:ring-4 focus:ring-primary-100 dark:border-surface-700 dark:bg-surface-900 dark:text-surface-50 dark:placeholder:text-surface-400 dark:focus:bg-surface-950 dark:focus:ring-primary-900/40 sm:pr-24"
                />
                <button
                  type="submit"
                  className="absolute right-1.5 top-1/2 hidden h-8 -translate-y-1/2 rounded-full bg-primary-600 px-4 text-xs font-semibold text-white shadow-sm transition-colors hover:bg-primary-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2 sm:inline-flex sm:items-center"
                >
                  Search
                </button>
              </div>
            </form>

            <div className="ml-auto flex shrink-0 items-center gap-2">
              <Button
                type="button"
                variant="ghost"
                size="icon"
                aria-label={`Open cart${itemCount > 0 ? `, ${itemCount} items` : ""}`}
                onClick={openDrawer}
                className="relative rounded-full bg-surface-100 text-surface-800 hover:bg-primary-50 hover:text-primary-700 dark:bg-surface-800 dark:text-surface-100 dark:hover:bg-primary-900/30"
              >
                <ShoppingCart className="h-5 w-5" aria-hidden="true" />
                {itemCount > 0 ? (
                  <span className="absolute -right-1 -top-1 flex min-h-5 min-w-5 items-center justify-center rounded-full bg-error-600 px-1 text-[11px] font-bold leading-none text-white">
                    {itemCount > 99 ? "99+" : itemCount}
                  </span>
                ) : null}
                {isFetching ? <span className="absolute bottom-1 right-1 h-2 w-2 rounded-full bg-primary-500" /> : null}
              </Button>

              <Button
                asChild
                variant={isSignedIn ? "secondary" : "primary"}
                size="sm"
                className="hidden rounded-full px-4 sm:inline-flex"
              >
                <Link href={isSignedIn ? "/account/orders" : "/login"}>
                  {isSignedIn ? (
                    <UserRound className="mr-2 h-4 w-4" aria-hidden="true" />
                  ) : (
                    <LogIn className="mr-2 h-4 w-4" aria-hidden="true" />
                  )}
                  {isReady && isSignedIn ? "Account" : "Sign in"}
                </Link>
              </Button>
            </div>
          </div>
        </div>
      </header>
    );
  }
);
Navbar.displayName = "Navbar";

export { Navbar };
