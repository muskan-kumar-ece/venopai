"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import type { AxiosError } from "axios";

import { useAuthStore } from "@/lib/stores/auth-store";

export function QueryProvider({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            refetchOnWindowFocus: false,
            retry: (failureCount, error) => {
              const axiosError = error as AxiosError | undefined;
              const status = axiosError?.response?.status;
              if (status === 401 || status === 403) {
                return false;
              }
              return failureCount < 2;
            },
          },
        },
      }),
  );

  const accessToken = useAuthStore((state) => state.accessToken);
  const isReady = useAuthStore((state) => state.isReady);

  useEffect(() => {
    if (!isReady) {
      return;
    }
    if (!accessToken) {
      queryClient.clear();
    }
  }, [accessToken, isReady, queryClient]);

  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}
