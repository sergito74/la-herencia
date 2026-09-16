const TONE_CLASSES = {
  success: "bg-status-success-bg text-status-success",
  warning: "bg-status-warning-bg text-status-warning",
  danger: "bg-status-danger-bg text-status-danger",
  neutral: "bg-status-neutral-bg text-status-neutral",
} as const;

export type BadgeTone = keyof typeof TONE_CLASSES;

/**
 * Pill de estado con color semántico (design/agroux-frontend-redesign.md
 * §4.2). Usar para cualquier campo de estado o resultado categórico
 * (cobrado/pendiente/vencido, origen resuelto/no disponible, etc.) en vez
 * de texto plano.
 */
export function StatusBadge({ label, tone }: { label: string; tone: BadgeTone }) {
  return (
    <span
      className={`inline-flex items-center rounded-sm px-2 py-0.5 text-xs font-medium ${TONE_CLASSES[tone]}`}
    >
      {label}
    </span>
  );
}
