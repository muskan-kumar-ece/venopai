/* eslint-disable no-console */
type EventPayload = Record<string, unknown>;

declare global {
  interface Window {
    Sentry?: {
      captureException: (error: unknown, ctx?: unknown) => void;
      captureMessage: (message: string, ctx?: unknown) => void;
    };
  }
}

export function trackEvent(event: string, payload: EventPayload = {}) {
  if (typeof window === "undefined") {
    return;
  }
  const body = { event, payload, ts: new Date().toISOString() };
  console.info("[analytics]", body);
}

export function captureApiFailure(error: unknown, payload: EventPayload = {}) {
  if (typeof window !== "undefined" && window.Sentry) {
    window.Sentry.captureException(error, { extra: payload });
  }
  console.error("[api_failure]", payload, error);
}

export function captureClientError(error: unknown, payload: EventPayload = {}) {
  if (typeof window !== "undefined" && window.Sentry) {
    window.Sentry.captureException(error, { extra: payload });
  }
  console.error("[client_error]", payload, error);
}
