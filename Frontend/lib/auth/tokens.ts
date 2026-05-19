const ACCESS_TOKEN_KEY = "access_token";
const REFRESH_TOKEN_KEY = "refresh_token";
const ACCESS_TOKEN_COOKIE = "access_token";
const REFRESH_TOKEN_COOKIE = "refresh_token";

export type TokenPair = {
  accessToken: string | null;
  refreshToken: string | null;
};

type JwtPayload = {
  exp?: number;
};

const tokenListeners = new Set<(tokens: TokenPair) => void>();

function isBrowser(): boolean {
  return typeof window !== "undefined";
}

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

export function getTokenExpiration(token: string | null): number | null {
  if (!token) {
    return null;
  }
  const payload = decodeJwtPayload(token);
  return payload?.exp ?? null;
}

export function isTokenExpired(token: string | null, skewSeconds = 30): boolean {
  const exp = getTokenExpiration(token);
  if (!exp) {
    return false;
  }
  const now = Math.floor(Date.now() / 1000);
  return exp <= now + skewSeconds;
}

function readCookie(name: string): string | null {
  if (!isBrowser()) {
    return null;
  }
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

function writeCookie(name: string, value: string | null) {
  if (!isBrowser()) {
    return;
  }
  const secure = window.location.protocol === "https:" ? "; secure" : "";
  if (!value) {
    document.cookie = `${name}=; path=/; max-age=0; samesite=lax${secure}`;
    return;
  }
  const exp = getTokenExpiration(value);
  const maxAge = exp ? Math.max(0, exp - Math.floor(Date.now() / 1000)) : null;
  const maxAgePart = maxAge != null ? `; max-age=${maxAge}` : "";
  document.cookie = `${name}=${encodeURIComponent(value)}; path=/; samesite=lax${secure}${maxAgePart}`;
}

function chooseFreshestToken(primary: string | null, secondary: string | null): string | null {
  if (!primary) {
    return secondary;
  }
  if (!secondary) {
    return primary;
  }
  const primaryExpired = isTokenExpired(primary, 0);
  const secondaryExpired = isTokenExpired(secondary, 0);
  if (primaryExpired && !secondaryExpired) {
    return secondary;
  }
  if (secondaryExpired && !primaryExpired) {
    return primary;
  }
  const primaryExp = getTokenExpiration(primary);
  const secondaryExp = getTokenExpiration(secondary);
  if (primaryExp && secondaryExp) {
    return primaryExp >= secondaryExp ? primary : secondary;
  }
  return primary;
}

function notifyListeners(tokens: TokenPair) {
  tokenListeners.forEach((listener) => {
    listener(tokens);
  });
}

export function subscribeTokenChanges(listener: (tokens: TokenPair) => void) {
  tokenListeners.add(listener);
  return () => tokenListeners.delete(listener);
}

export function loadTokenPair(): TokenPair {
  if (!isBrowser()) {
    return { accessToken: null, refreshToken: null };
  }
  const accessLocal = window.localStorage.getItem(ACCESS_TOKEN_KEY);
  const refreshLocal = window.localStorage.getItem(REFRESH_TOKEN_KEY);
  const accessCookie = readCookie(ACCESS_TOKEN_COOKIE);
  const refreshCookie = readCookie(REFRESH_TOKEN_COOKIE);

  return {
    accessToken: chooseFreshestToken(accessLocal, accessCookie),
    refreshToken: chooseFreshestToken(refreshLocal, refreshCookie),
  };
}

export function persistTokenPair(accessToken: string | null, refreshToken: string | null) {
  if (!isBrowser()) {
    return;
  }
  if (accessToken) {
    window.localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
  } else {
    window.localStorage.removeItem(ACCESS_TOKEN_KEY);
  }
  if (refreshToken) {
    window.localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
  } else {
    window.localStorage.removeItem(REFRESH_TOKEN_KEY);
  }

  writeCookie(ACCESS_TOKEN_COOKIE, accessToken);
  writeCookie(REFRESH_TOKEN_COOKIE, refreshToken);

  notifyListeners({ accessToken, refreshToken });
}

export function clearTokenPair() {
  persistTokenPair(null, null);
}

export function getAccessToken(): string | null {
  return loadTokenPair().accessToken;
}

export function getRefreshToken(): string | null {
  return loadTokenPair().refreshToken;
}
