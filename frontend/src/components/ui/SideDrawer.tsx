"use client";

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
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  /** Ancho máximo del panel (clase de Tailwind), ej. "max-w-6xl" para paneles de trabajo. */
  maxWidthClass?: string;
}) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-20">
      <div
        className="absolute inset-0 bg-ink-primary/30"
        onClick={onClose}
        aria-hidden="true"
      />
      <div
        className={`absolute right-0 top-0 flex h-full w-full ${maxWidthClass} flex-col overflow-y-auto border-l border-border bg-surface shadow-lg`}
      >
        <div className="flex items-center justify-between border-b border-border px-4 py-3">
          <h2 className="font-semibold text-ink-primary">{title}</h2>
          <button
            type="button"
            onClick={onClose}
            className="text-ink-secondary hover:text-ink-primary"
            aria-label="Cerrar"
          >
            ✕
          </button>
        </div>
        <div className="flex-1 p-4">{children}</div>
      </div>
    </div>
  );
}
