"use client";

import { createContext, useCallback, useContext, useRef, useState } from "react";

export type ToastTone = "success" | "danger" | "neutral";

interface ToastItem {
  id: number;
  message: string;
  tone: ToastTone;
}

interface ToastContextValue {
  showToast: (message: string, tone?: ToastTone) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

const TONE_CLASSES: Record<ToastTone, string> = {
  success: "border-status-success bg-status-success-bg text-status-success",
  danger: "border-status-danger bg-status-danger-bg text-status-danger",
  neutral: "border-border bg-surface text-ink-primary",
};

const AUTO_DISMISS_MS = 4000;

/**
 * Notificaciones toast — feature "amigable" pedida por el usuario, en vez de
 * éxito/error silencioso en la primera acción de escritura real de la app
 * (marcar cuota de arrendamiento como cobrada/pendiente). Justificación:
 * patrones de SaaS moderno (shadcn/ui "Sonner"/toast) y el shell bar de SAP
 * Fiori confirman feedback transitorio no bloqueante como estándar en vez de
 * un `<p>` de estado o un `alert()`. Sin dependencia nueva — contenedor
 * simple con setTimeout, reversible.
 */
export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const nextId = useRef(0);

  const dismiss = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const showToast = useCallback(
    (message: string, tone: ToastTone = "neutral") => {
      const id = nextId.current++;
      setToasts((prev) => [...prev, { id, message, tone }]);
      setTimeout(() => dismiss(id), AUTO_DISMISS_MS);
    },
    [dismiss],
  );

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      <div
        aria-live="polite"
        className="pointer-events-none fixed right-4 top-4 z-50 flex w-full max-w-sm flex-col gap-2"
      >
        {toasts.map((t) => (
          <div
            key={t.id}
            role="status"
            className={`pointer-events-auto flex items-start justify-between gap-3 rounded-md border px-4 py-3 text-sm shadow-lg ${TONE_CLASSES[t.tone]}`}
          >
            <span>{t.message}</span>
            <button
              type="button"
              onClick={() => dismiss(t.id)}
              aria-label="Cerrar notificación"
              className="text-ink-muted hover:text-ink-primary"
            >
              ×
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    throw new Error("useToast debe usarse dentro de <ToastProvider>");
  }
  return ctx;
}
