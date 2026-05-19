"use client";

import { create } from "zustand";

import * as authApi from "@/lib/api/auth";
import {
  clearTokenPair,
  isTokenExpired,
  loadTokenPair,
  persistTokenPair,
  subscribeTokenChanges,
} from "@/lib/auth/tokens";

type LogoutReason = "expired" | "manual" | null;

let initializePromise: Promise<void> | null = null;

type AuthState = {
  accessToken: string | null;
  refreshToken: string | null;
  isReady: boolean;
  isRefreshing: boolean;
  logoutReason: LogoutReason;
  initialize: () => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  logout: (reason?: LogoutReason) => void;
  clearLogoutReason: () => void;
};

export const useAuthStore = create<AuthState>((set, get) => {
  subscribeTokenChanges((tokens) => {
    const previous = get();
    const wasAuthenticated = Boolean(previous.accessToken);
    set({ accessToken: tokens.accessToken, refreshToken: tokens.refreshToken });
    if (
      previous.isReady &&
      previous.logoutReason == null &&
      wasAuthenticated &&
      !tokens.accessToken
    ) {
      set({ logoutReason: "expired" });
    }
  });

  return {
    accessToken: null,
    refreshToken: null,
    isReady: false,
    isRefreshing: false,
    logoutReason: null,
    initialize: async () => {
      if (initializePromise) {
        return initializePromise;
      }
      if (typeof window === "undefined") {
        set({ isReady: true });
        return Promise.resolve();
      }

      initializePromise = (async () => {
        const stored = loadTokenPair();
        const hasValidAccess = stored.accessToken && !isTokenExpired(stored.accessToken);
        if (hasValidAccess) {
          persistTokenPair(stored.accessToken, stored.refreshToken);
          set({
            accessToken: stored.accessToken,
            refreshToken: stored.refreshToken,
            isReady: true,
            logoutReason: null,
          });
          return;
        }

        if (stored.refreshToken && !isTokenExpired(stored.refreshToken)) {
          set({ isRefreshing: true });
          try {
            const refreshed = await authApi.refresh({ refresh: stored.refreshToken });
            const nextRefresh = refreshed.refresh ?? stored.refreshToken;
            persistTokenPair(refreshed.access, nextRefresh);
            set({
              accessToken: refreshed.access,
              refreshToken: nextRefresh,
              logoutReason: null,
            });
          } catch {
            clearTokenPair();
            set({ accessToken: null, refreshToken: null, logoutReason: "expired" });
          } finally {
            set({ isRefreshing: false, isReady: true });
          }
          return;
        }

        clearTokenPair();
        set({ accessToken: null, refreshToken: null, isReady: true });
      })();

      return initializePromise.finally(() => {
        initializePromise = null;
      });
    },
    login: async (email: string, password: string) => {
      const token = await authApi.login({ email, password });
      persistTokenPair(token.access, token.refresh);
      set({
        accessToken: token.access,
        refreshToken: token.refresh,
        logoutReason: null,
        isReady: true,
      });
    },
    logout: (reason = "manual") => {
      clearTokenPair();
      set({ accessToken: null, refreshToken: null, logoutReason: reason, isReady: true });
    },
    clearLogoutReason: () => {
      set({ logoutReason: null });
    },
  };
});
