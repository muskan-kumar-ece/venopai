"use client";

import { useEffect } from "react";

import { useAuthStore } from "@/lib/stores/auth-store";

type AuthContextValue = {
  accessToken: string | null;
  isReady: boolean;
  isRefreshing: boolean;
  logoutReason: "expired" | "manual" | null;
  login: (email: string, password: string) => Promise<void>;
  logout: (reason?: "expired" | "manual" | null) => void;
  clearLogoutReason: () => void;
};

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const initialize = useAuthStore((state) => state.initialize);

  useEffect(() => {
    void initialize();
  }, [initialize]);

  return <>{children}</>;
}

export const useAuth = (): AuthContextValue => useAuthStore((state) => state);
