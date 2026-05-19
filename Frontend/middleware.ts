import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type JwtPayload = {
  exp?: number;
};

function decodeJwtPayload(token: string): JwtPayload | null {
  const payload = token.split(".")[1];
  if (!payload) {
    return null;
  }
  try {
    const base64 = payload.replace(/-/g, "+").replace(/_/g, "/");
    const padded = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), "=");
    return JSON.parse(atob(padded)) as JwtPayload;
  } catch {
    return null;
  }
}

function getTokenExpiration(token: string | null): number | null {
  if (!token) {
    return null;
  }
  return decodeJwtPayload(token)?.exp ?? null;
}

function isTokenExpired(token: string | null, skewSeconds = 30): boolean {
  const exp = getTokenExpiration(token);
  if (!exp) {
    return false;
  }
  const now = Math.floor(Date.now() / 1000);
  return exp <= now + skewSeconds;
}

function setTokenCookie(response: NextResponse, name: string, token: string | null, secure: boolean) {
  if (!token) {
    response.cookies.delete(name);
    return;
  }
  const exp = getTokenExpiration(token);
  const maxAge = exp ? Math.max(0, exp - Math.floor(Date.now() / 1000)) : undefined;
  response.cookies.set(name, token, {
    path: "/",
    sameSite: "lax",
    secure,
    maxAge,
  });
}

async function refreshAccessToken(refreshToken: string) {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/auth/token/refresh/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ refresh: refreshToken }),
      cache: "no-store",
    });
    if (!response.ok) {
      return null;
    }
    return (await response.json()) as { access: string; refresh?: string };
  } catch (error) {
    console.error("Token refresh failed in middleware", error);
    return null;
  }
}

function redirectToLogin(request: NextRequest, reason?: "expired" | "missing") {
  const loginUrl = new URL("/login", request.url);
  loginUrl.searchParams.set("next", request.nextUrl.pathname);
  if (reason) {
    loginUrl.searchParams.set("reason", reason);
  }
  const response = NextResponse.redirect(loginUrl);
  response.cookies.delete("access_token");
  response.cookies.delete("refresh_token");
  return response;
}

export async function middleware(request: NextRequest) {
  let accessToken = request.cookies.get("access_token")?.value ?? null;
  let refreshToken = request.cookies.get("refresh_token")?.value ?? null;
  let didRefresh = false;
  const isSecureRequest = request.nextUrl.protocol === "https:";

  if (!accessToken || isTokenExpired(accessToken)) {
    if (refreshToken && !isTokenExpired(refreshToken)) {
      const refreshed = await refreshAccessToken(refreshToken);
      if (refreshed?.access) {
        accessToken = refreshed.access;
        refreshToken = refreshed.refresh ?? refreshToken;
        didRefresh = true;
      }
    }
  }

  if (!accessToken || isTokenExpired(accessToken)) {
    return redirectToLogin(request, "expired");
  }

  const requiresAdminAccess =
    request.nextUrl.pathname.startsWith("/admin") || request.nextUrl.pathname.startsWith("/dashboard");

  if (requiresAdminAccess) {
    try {
      // Use the dedicated read-only /users/me/ endpoint to check staff status.
      // This avoids the previous approach of making a write (POST) request to
      // the products endpoint, which was semantically incorrect and fragile.
      const response = await fetch(`${API_BASE_URL}/api/v1/users/me/`, {
        method: "GET",
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
        cache: "no-store",
      });

      if (response.status === 401) {
        if (refreshToken && !didRefresh) {
          const refreshed = await refreshAccessToken(refreshToken);
          if (refreshed?.access) {
            accessToken = refreshed.access;
            refreshToken = refreshed.refresh ?? refreshToken;
            didRefresh = true;
          } else {
            return redirectToLogin(request, "expired");
          }
        } else {
          return redirectToLogin(request, "expired");
        }

        const retryResponse = await fetch(`${API_BASE_URL}/api/v1/users/me/`, {
          method: "GET",
          headers: {
            Authorization: `Bearer ${accessToken}`,
          },
          cache: "no-store",
        });
        if (!retryResponse.ok) {
          return redirectToLogin(request, "expired");
        }
        const retryUser = (await retryResponse.json()) as { is_staff?: boolean };
        if (!retryUser.is_staff) {
          return NextResponse.redirect(new URL("/", request.url));
        }
        const responseWithRefresh = NextResponse.next();
        setTokenCookie(responseWithRefresh, "access_token", accessToken, isSecureRequest);
        if (refreshToken) {
          setTokenCookie(responseWithRefresh, "refresh_token", refreshToken, isSecureRequest);
        }
        return responseWithRefresh;
      }

      if (!response.ok) {
        // Unexpected error – deny access rather than silently allow
        return NextResponse.redirect(new URL("/", request.url));
      }

      const user = await response.json() as { is_staff?: boolean };
      if (!user.is_staff) {
        return NextResponse.redirect(new URL("/", request.url));
      }
    } catch (error) {
      console.error("Admin route staff check failed", error);
      return NextResponse.redirect(new URL("/", request.url));
    }
  }

  const response = NextResponse.next();
  if (didRefresh) {
    setTokenCookie(response, "access_token", accessToken, isSecureRequest);
    if (refreshToken) {
      setTokenCookie(response, "refresh_token", refreshToken, isSecureRequest);
    }
  }
  return response;
}

export const config = {
  matcher: [
    "/cart/:path*",
    "/checkout/:path*",
    "/referral/:path*",
    "/account/:path*",
    "/admin/:path*",
    "/dashboard/:path*",
  ],
};
