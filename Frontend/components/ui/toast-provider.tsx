"use client";

import * as React from "react";

import { Toast } from "@/components/ui/toast";
import { type ToastItem, useToast } from "@/components/ui/use-toast";

const EXIT_DURATION_MS = 200;
const MAX_VISIBLE_TOASTS = 4;

type RenderToast = ToastItem & { exiting?: boolean };

function ToastProvider() {
  const { toasts, dismiss } = useToast();
  const [renderToasts, setRenderToasts] = React.useState<RenderToast[]>(toasts);
  const [prefersReducedMotion, setPrefersReducedMotion] = React.useState(false);
  const removalTimersRef = React.useRef<Map<string, number>>(new Map());
  const dismissTimersRef = React.useRef<Map<string, number>>(new Map());

  React.useEffect(() => {
    const mediaQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    const updatePreference = () => setPrefersReducedMotion(mediaQuery.matches);

    updatePreference();
    mediaQuery.addEventListener("change", updatePreference);
    return () => mediaQuery.removeEventListener("change", updatePreference);
  }, []);

  React.useEffect(() => {
    setRenderToasts((prev) => {
      const incomingIds = new Set(toasts.map((toast) => toast.id));
      const activeToasts = toasts.map((toast) => {
        const existing = prev.find((item) => item.id === toast.id);
        return existing?.exiting ? { ...toast, exiting: true } : { ...toast };
      });

      if (prefersReducedMotion) {
        return activeToasts;
      }

      const exitingToasts = prev
        .filter((toast) => !incomingIds.has(toast.id))
        .map((toast) => ({ ...toast, exiting: true }));

      const limitedActiveToasts = activeToasts.slice(0, MAX_VISIBLE_TOASTS);
      const remainingSlots = MAX_VISIBLE_TOASTS - limitedActiveToasts.length;
      const limitedExitingToasts = exitingToasts.slice(0, Math.max(remainingSlots, 0));

      return [...limitedActiveToasts, ...limitedExitingToasts];
    });
  }, [toasts, prefersReducedMotion]);

  React.useEffect(() => {
    if (prefersReducedMotion) {
      setRenderToasts((prev) => prev.filter((toast) => !toast.exiting));
      return;
    }

    const timers = removalTimersRef.current;
    const exitingIds = new Set(renderToasts.filter((toast) => toast.exiting).map((toast) => toast.id));

    renderToasts.forEach((toast) => {
      if (toast.exiting && !timers.has(toast.id)) {
        timers.set(
          toast.id,
          window.setTimeout(() => {
            setRenderToasts((prev) => prev.filter((item) => item.id !== toast.id));
            timers.delete(toast.id);
          }, EXIT_DURATION_MS),
        );
      }
    });
    timers.forEach((timer, id) => {
      if (!exitingIds.has(id)) {
        window.clearTimeout(timer);
        timers.delete(id);
      }
    });
  }, [renderToasts, prefersReducedMotion]);

  React.useEffect(
    () => () => {
      removalTimersRef.current.forEach((timer) => window.clearTimeout(timer));
      removalTimersRef.current.clear();
      dismissTimersRef.current.forEach((timer) => window.clearTimeout(timer));
      dismissTimersRef.current.clear();
    },
    [],
  );

  const handleClose = React.useCallback(
    (id: string) => {
      if (prefersReducedMotion) {
        dismiss(id);
        return;
      }

      setRenderToasts((prev) =>
        prev.map((toast) => (toast.id === id ? { ...toast, exiting: true } : toast)),
      );
      if (!dismissTimersRef.current.has(id)) {
        dismissTimersRef.current.set(
          id,
          window.setTimeout(() => {
            dismiss(id);
            dismissTimersRef.current.delete(id);
          }, EXIT_DURATION_MS),
        );
      }
    },
    [dismiss, prefersReducedMotion],
  );

  return (
    <div
      aria-live="polite"
      aria-relevant="additions text"
      className="pointer-events-none fixed inset-x-4 bottom-4 z-50 flex flex-col-reverse gap-3 sm:inset-x-auto sm:bottom-auto sm:right-4 sm:top-4 sm:flex-col"
    >
      {renderToasts.map((item) => (
        <Toast
          key={item.id}
          variant={item.variant}
          title={item.title}
          description={item.description}
          exiting={item.exiting}
          onClose={() => handleClose(item.id)}
          className="pointer-events-auto"
        />
      ))}
    </div>
  );
}

export { ToastProvider };
