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

export function EmptyState({ message }: { message: string }) {
  return (
    <div className="rounded-md border border-border bg-surface p-6 text-center text-sm text-ink-secondary">
      {message}
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
