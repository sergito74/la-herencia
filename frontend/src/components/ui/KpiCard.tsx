import type { BadgeTone } from "@/components/ui/StatusBadge";

const VALUE_TONE_CLASSES: Record<BadgeTone, string> = {
  success: "text-status-success",
  warning: "text-status-warning",
  danger: "text-status-danger",
  neutral: "text-ink-primary",
};

/**
 * Tarjeta de resumen (design/agroux-frontend-redesign.md §4.5). Usar solo
 * con datos reales agregables ya disponibles — no inventar métricas que
 * el sistema no expone (ej. márgenes/rentabilidad).
 */
export function KpiCard({
  label,
  value,
  tone = "neutral",
}: {
  label: string;
  value: string;
  tone?: BadgeTone;
}) {
  return (
    <div className="rounded-md border border-border bg-surface p-4">
      <p className="text-xs uppercase tracking-wide text-ink-secondary">{label}</p>
      <p className={`font-data mt-1 text-2xl font-semibold ${VALUE_TONE_CLASSES[tone]}`}>
        {value}
      </p>
    </div>
  );
}
