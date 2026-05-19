import axios from "axios";

import type { JwtPair, JwtRefreshResponse } from "@/lib/api/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const authClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
});

export async function login(payload: { email: string; password: string }) {
  const { data } = await authClient.post<JwtPair>("/api/v1/auth/token/", payload);
  return data;
}

export async function refresh(payload: { refresh: string }) {
  const { data } = await authClient.post<JwtRefreshResponse>("/api/v1/auth/token/refresh/", payload);
  return data;
}
