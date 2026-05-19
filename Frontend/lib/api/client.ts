import axios, {
  AxiosError,
  type AxiosResponse,
  type InternalAxiosRequestConfig,
} from "axios";

import type { JwtRefreshResponse } from "@/lib/api/types";
import {
  clearTokenPair,
  getAccessToken,
  getRefreshToken,
  isTokenExpired,
  persistTokenPair,
} from "@/lib/auth/tokens";
import { captureApiFailure, trackEvent } from "@/lib/observability";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const AUTH_REFRESH_ENDPOINT = "/api/v1/auth/token/refresh/";
const AUTH_LOGIN_ENDPOINT = "/api/v1/auth/token/";

type RefreshableRequestConfig = InternalAxiosRequestConfig & {
  _retry?: boolean;
  skipAuthRefresh?: boolean;
};

let refreshPromise: Promise<string | null> | null = null;
let authFailureRedirected = false;

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
});

const refreshClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
});

function isAuthEndpoint(url?: string) {
  if (!url) {
    return false;
  }
  return url.includes(AUTH_REFRESH_ENDPOINT) || url.includes(AUTH_LOGIN_ENDPOINT);
}

async function refreshAccessToken(): Promise<string | null> {
  const refreshToken = getRefreshToken();
  if (!refreshToken || isTokenExpired(refreshToken)) {
    clearTokenPair();
    return null;
  }

  if (!refreshPromise) {
    refreshPromise = refreshClient
      .post<JwtRefreshResponse>(AUTH_REFRESH_ENDPOINT, { refresh: refreshToken })
      .then((response) => {
        const nextAccess = response.data.access;
        const nextRefresh = response.data.refresh ?? refreshToken;
        persistTokenPair(nextAccess, nextRefresh);
        return nextAccess;
      })
      .catch(() => {
        clearTokenPair();
        return null;
      })
      .finally(() => {
        refreshPromise = null;
      });
  }

  return refreshPromise;
}

function isProtectedPath(pathname: string) {
  return ["/cart", "/checkout", "/referral", "/admin", "/dashboard", "/account"].some((prefix) =>
    pathname.startsWith(prefix),
  );
}

function handleAuthFailure() {
  clearTokenPair();
  if (typeof window === "undefined" || authFailureRedirected) {
    return;
  }
  const pathname = window.location.pathname;
  if (pathname.startsWith("/login")) {
    return;
  }
  if (isProtectedPath(pathname)) {
    authFailureRedirected = true;
    const next = encodeURIComponent(pathname);
    window.location.assign(`/login?reason=expired&next=${next}`);
  }
}

apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const requestId = `fe-${Date.now()}-${Math.random().toString(16).slice(2, 10)}`;
  const token = getAccessToken();
  if (token && !config.headers.Authorization) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  config.headers["X-Request-ID"] = requestId;
  return config;
});

apiClient.interceptors.response.use(
  (response: AxiosResponse) => {
    const requestId = response.headers["x-request-id"];
    if (requestId) {
      trackEvent("api_request_success", { path: response.config.url, status: response.status, request_id: requestId });
    }
    return response;
  },
  async (error: AxiosError) => {
    const responseStatus = error.response?.status;
    const originalRequest = error.config as RefreshableRequestConfig | undefined;

    if (!originalRequest) {
      return Promise.reject(error);
    }

    const shouldSkipRefresh =
      originalRequest.skipAuthRefresh ||
      originalRequest._retry ||
      isAuthEndpoint(originalRequest.url);

    if (responseStatus !== 401 || shouldSkipRefresh) {
      captureApiFailure(error, {
        path: originalRequest.url,
        method: originalRequest.method,
        status: responseStatus,
        request_id: error.response?.headers?.["x-request-id"],
      });
      return Promise.reject(error);
    }

    originalRequest._retry = true;
    const nextAccessToken = await refreshAccessToken();
    if (!nextAccessToken) {
      handleAuthFailure();
      trackEvent("auth_refresh_failed", { path: originalRequest.url, status: responseStatus });
      return Promise.reject(error);
    }

    originalRequest.headers = originalRequest.headers ?? {};
    originalRequest.headers.Authorization = `Bearer ${nextAccessToken}`;
    return apiClient(originalRequest);
  },
);
