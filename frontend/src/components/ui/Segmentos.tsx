"use client";

/** Selector de opciones excluyentes en forma de chips (18/11/2026): un solo estilo para elegir medio, vista o filtro
 * (Tesorería, Cajas, Imputación, Resultado, Planificación). Las secciones de una pantalla usan Tabs. */
export function Segmentos<T extends string>({ opciones, valor, onChange, etiqueta, size = "md" }: {
  opciones: { id: T; label: React.ReactNode; aviso?: number }[];
  valor: T;
  onChange: (id: T) => void;
  etiqueta?: string;
  size?: "sm" | "md";
}) {
  return (
    <div role="radiogroup" aria-label={etiqueta} className="inline-flex flex-wrap gap-0.5 rounded-lg border border-border bg-surface-sunken/70 p-0.5">
      {opciones.map((o) => {
        const activo = o.id === valor;
        return (
          <button key={o.id} type="button" role="radio" aria-checked={activo} onClick={() => onChange(o.id)}
            className={`inline-flex items-center gap-1.5 rounded-md ${size === "sm" ? "px-2 py-0.5 text-[13px]" : "px-2.5 py-1 text-sm"} font-medium transition-colors ${
              activo ? "bg-surface text-finance shadow-sm ring-1 ring-border" : "text-ink-secondary hover:bg-surface/70 hover:text-ink-primary"}`}>
            {o.label}
            {!!o.aviso && <span className="rounded-full bg-status-warning px-1.5 text-[11px] font-semibold leading-4 text-white">{o.aviso}</span>}
          </button>
        );
      })}
    </div>
  );
}
