"use client";

import * as React from "react";

export type ToastVariant = "success" | "error" | "warning" | "info";

export interface ToastInput {
  title?: React.ReactNode;
  description?: React.ReactNode;
  variant?: ToastVariant;
}

export interface ToastItem extends ToastInput {
  id: string;
}

interface ToastState {
  toasts: ToastItem[];
}

const TOAST_LIMIT = 4;
const TOAST_DURATION = 4000;
let memoryState: ToastState = { toasts: [] };
const listeners = new Set<(state: ToastState) => void>();
const toastTimeouts = new Map<string, ReturnType<typeof setTimeout>>();

function emit(state: ToastState) {
  memoryState = state;
  listeners.forEach((listener) => listener(memoryState));
}

function dismiss(id: string) {
  const timeout = toastTimeouts.get(id);
  if (timeout) {
    clearTimeout(timeout);
    toastTimeouts.delete(id);
  }

  emit({
    toasts: memoryState.toasts.filter((toast) => toast.id !== id),
  });
}

function toast({ title, description, variant = "info" }: ToastInput) {
  const id =
    typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
      ? crypto.randomUUID()
      : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
  const nextToasts = [{ id, title, description, variant }, ...memoryState.toasts].slice(
    0,
    TOAST_LIMIT,
  );

  memoryState.toasts
    .filter((item) => !nextToasts.some((toastItem) => toastItem.id === item.id))
    .forEach((item) => {
      const timeout = toastTimeouts.get(item.id);
      if (timeout) {
        clearTimeout(timeout);
        toastTimeouts.delete(item.id);
      }
    });

  const timeout = setTimeout(() => dismiss(id), TOAST_DURATION);
  toastTimeouts.set(id, timeout);

  emit({
    toasts: nextToasts,
  });
  return id;
}

toast.success = (input: Omit<ToastInput, "variant">) => toast({ ...input, variant: "success" });
toast.error = (input: Omit<ToastInput, "variant">) => toast({ ...input, variant: "error" });
toast.warning = (input: Omit<ToastInput, "variant">) => toast({ ...input, variant: "warning" });
toast.info = (input: Omit<ToastInput, "variant">) => toast({ ...input, variant: "info" });
toast.loading = (input: Omit<ToastInput, "variant">) => toast({ title: input.title ?? "Loading", description: input.description, variant: "info" });

function useToast() {
  const [state, setState] = React.useState<ToastState>(memoryState);

  React.useEffect(() => {
    listeners.add(setState);
    return () => {
      listeners.delete(setState);
    };
  }, []);

  return {
    ...state,
    toast,
    dismiss,
  };
}

export { useToast, toast, dismiss };
