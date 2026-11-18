"use client";

import Link from "next/link";
import { useEffect } from "react";

/**
 * Panel lateral para ver detalle sin abandonar el listado
 * (design/agroux-frontend-redesign.md §4.3).
 */
export function SideDrawer({
  open,
  onClose,
  title,
  children,
  maxWidthClass = "max-w-md",
  subtitulo,
  verCompleto,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  /** Ancho máximo del panel (clase de Tailwind), ej. "max-w-6xl" para paneles de trabajo. */
  maxWidthClass?: string;
  subtitulo?: React.ReactNode;
  /** Spec 051 FR-011: acceso a la pantalla completa del registro. */
  verCompleto?: string;
}) {
  useEffect(() => {
    if (!open) return;
    const esc = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", esc);
    return () => document.removeEventListener("keydown", esc);
  }, [open, onClose]);
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-40" role="dialog" aria-modal="true" aria-label={title}>
      <div
        className="absolute inset-0 bg-ink-primary/30"
        onClick={onClose}
        aria-hidden="true"
      />
      <div
        className={`absolute right-0 top-0 flex h-full w-full ${maxWidthClass} flex-col overflow-y-auto border-l border-border bg-surface shadow-lg`}
      >
        <div className="flex items-center justify-between gap-3 border-b border-border px-4 py-3">
          <div className="min-w-0">
            <h2 className="truncate font-semibold text-ink-primary">{title}</h2>
            {subtitulo && <p className="truncate text-xs text-ink-secondary">{subtitulo}</p>}
          </div>
          <div className="flex shrink-0 items-center gap-3">
          {verCompleto && <Link href={verCompleto} className="text-xs font-medium text-finance hover:underline">Abrir completo →</Link>}
          <button
            type="button"
            onClick={onClose}
            className="text-ink-secondary hover:text-ink-primary"
            aria-label="Cerrar"
          >
            ✕
          </button>
          </div>
        </div>
        <div className="flex-1 p-4">{children}</div>
      </div>
    </div>
  );
}
