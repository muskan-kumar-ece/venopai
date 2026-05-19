import type { Metadata } from "next";

import { AuthProvider } from "@/components/providers/auth-provider";
import { ObservabilityProvider } from "@/components/providers/observability-provider";
import { QueryProvider } from "@/components/providers/query-provider";
import "./globals.css";

export const metadata: Metadata = {
  title: "Venopai Commerce",
  description: "Premium ecommerce frontend",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-dvh bg-neutral-50 font-sans text-neutral-800 dark:bg-neutral-900 dark:text-neutral-100">
        <QueryProvider>
          <ObservabilityProvider>
            <AuthProvider>{children}</AuthProvider>
          </ObservabilityProvider>
        </QueryProvider>
      </body>
    </html>
  );
}
