/**
 * Estados fijos de carga/vacío/error (design/agroux-frontend-redesign.md
 * §4.4) — reemplazan los `<p>` sueltos repetidos en cada módulo.
 */

export function LoadingState({ rows = 4 }: { rows?: number }) {
  return (
    <div
      className="animate-pulse space-y-2 rounded-md border border-border bg-surface p-4"
      role="status"
      aria-label="Cargando"
    >
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="h-4 rounded bg-surface-sunken" />
      ))}
    </div>
  );
}

/** Estado vacío (18/11/2026): ícono, mensaje, una pista de qué hacer y una acción opcional, en vez de una línea gris
 * suelta. `message` sigue siendo el texto principal, así no cambia ninguna pantalla que ya lo usa. */
export function EmptyState({ message, detalle, accion, icono = "vacio" }: {
  message: string;
  detalle?: React.ReactNode;
  accion?: React.ReactNode;
  icono?: "vacio" | "buscar" | "ok";
}) {
  const trazo = {
    vacio: <path d="M4 7h16M6 7l1.5 12h9L18 7M9 7V5h6v2" />,
    buscar: <><circle cx="11" cy="11" r="6" /><path d="m20 20-4.5-4.5" /></>,
    ok: <path d="m5 12 4.5 4.5L19 7" />,
  }[icono];
  return (
    <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed border-border-strong bg-surface px-6 py-10 text-center">
      <span className={`flex h-11 w-11 items-center justify-center rounded-full ${icono === "ok" ? "bg-status-success-bg text-status-success" : "bg-surface-sunken text-ink-muted"}`}>
        <svg viewBox="0 0 24 24" className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round" aria-hidden>{trazo}</svg>
      </span>
      <p className="text-sm font-medium text-ink-primary">{message}</p>
      {detalle && <p className="max-w-md text-sm text-ink-secondary">{detalle}</p>}
      {accion && <div className="mt-2">{accion}</div>}
    </div>
  );
}

export function ErrorState({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div className="flex items-center justify-between rounded-md border border-status-danger bg-status-danger-bg px-4 py-3 text-sm text-status-danger">
      <span>{message}</span>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="rounded-sm border border-status-danger px-2 py-1 text-xs font-medium hover:bg-status-danger hover:text-white"
        >
          Reintentar
        </button>
      )}
    </div>
  );
}
