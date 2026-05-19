import { CartDrawer } from "@/components/layout/cart-drawer";
import { Navbar } from "@/components/navigation/navbar";

export function SiteShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-dvh bg-neutral-50 dark:bg-neutral-950">
      <Navbar />
      <main className="mx-auto w-full max-w-[1280px] px-4 py-6 sm:px-6 sm:py-8 lg:px-8">{children}</main>
      <CartDrawer />
    </div>
  );
}
