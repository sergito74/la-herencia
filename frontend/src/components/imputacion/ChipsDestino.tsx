import { formatMoneda } from "@/lib/format";
import type { DestinoDoc, Familia } from "@/services/imputacionDocumentosApi";

/** Color neutro por familia de destino; nunca rojo (auditoría de diseño 18/11/2026). */
export const COLOR_FAMILIA: Record<Familia, string> = {
  agricultura: "border-agro/30 bg-agro-light text-agro",
  ganaderia: "border-amber-300/50 bg-amber-50 text-amber-800",
  administracion: "border-border bg-surface-sunken text-ink-secondary",
  stock: "border-finance/30 bg-finance-light text-finance",
  aviso: "border-status-warning/40 bg-status-warning-bg text-status-warning",
};

export function ChipDestino({ d, conImporte = false }: { d: Pick<DestinoDoc, "etiqueta" | "familia" | "importe" | "porcentaje">; conImporte?: boolean }) {
  return (
    <span className={`inline-flex max-w-[14rem] items-center gap-1 truncate rounded-full border px-2 py-0.5 text-xs ${COLOR_FAMILIA[d.familia]}`}
      title={`${d.etiqueta}: ${formatMoneda(d.importe)}`}>
      <span className="truncate">{d.etiqueta}</span>
      {conImporte ? <span className="font-data">{formatMoneda(d.importe)}</span>
        : d.porcentaje != null && d.porcentaje < 100 ? <span className="font-data opacity-75">{d.porcentaje}%</span> : null}
    </span>
  );
}

/** Hasta 2 chips y "+N" (el resto en el título). */
export function ChipsDestino({ destinos }: { destinos: DestinoDoc[] }) {
  if (!destinos.length) return <span className="text-xs text-ink-muted">No se imputa</span>;
  const resto = destinos.slice(2);
  return (
    <span className="flex flex-wrap items-center gap-1">
      {destinos.slice(0, 2).map((d) => <ChipDestino key={d.clave} d={d} />)}
      {resto.length > 0 && <span className="text-xs text-ink-secondary" title={resto.map((d) => `${d.etiqueta} ${formatMoneda(d.importe)}`).join(" · ")}>+{resto.length}</span>}
    </span>
  );
}
