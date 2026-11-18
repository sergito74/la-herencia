import { formatMoneda } from "@/lib/format";

/** Saldo con sentido (18/11/2026): el número va en el color normal y una etiqueta chica dice para qué lado está.
 * El rojo/verde por signo confundía (un saldo a favor salía en verde con signo menos) y el rojo queda solo para
 * alertas. `negativo`/`positivo` son las etiquetas de cada lado según la cuenta. */
export function Saldo({ valor, moneda = "Pesos", negativo, positivo, absoluto = true, className = "" }: {
  valor: number | null | undefined;
  moneda?: "Pesos" | "Dolares";
  negativo: string;
  positivo: string;
  /** Mostrar el número sin signo (el sentido lo da la etiqueta). */
  absoluto?: boolean;
  className?: string;
}) {
  if (valor == null) return <span className="text-ink-muted">—</span>;
  if (Math.abs(valor) < 0.005) return <span className={`text-ink-muted ${className}`}>{formatMoneda(0, moneda)}</span>;
  const etiqueta = valor < 0 ? negativo : positivo;
  return (
    <span className={`inline-flex items-baseline justify-end gap-1.5 whitespace-nowrap ${className}`}>
      <span className="font-data tabular-nums text-ink-primary">{formatMoneda(absoluto ? Math.abs(valor) : valor, moneda)}</span>
      <span className="rounded-sm bg-surface-sunken px-1.5 text-[11px] font-medium text-ink-secondary">{etiqueta}</span>
    </span>
  );
}
