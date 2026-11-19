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
    <div className="flex items-baseline gap-2 rounded-md border border-border bg-surface px-3 py-2">
      <p className="text-[11px] font-medium uppercase tracking-wide text-ink-muted">{label}</p>
      <p className={`font-data text-base font-semibold ${VALUE_TONE_CLASSES[tone]}`}>
        {value}
      </p>
    </div>
  );
}
