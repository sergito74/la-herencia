"use client";
import { Flotante } from "@/components/ui/Flotante";
import { useEffect, useRef, useState } from "react";

/** Rango de fechas con atajos (spec 051 FR-008): este mes, mes pasado, últimos 90 días, campaña actual (1/7–30/6),
 * campaña anterior, año calendario, rango libre y sin filtro. Trabaja con fechas ISO (aaaa-mm-dd); "" = sin límite. */
export type Rango = { desde: string; hasta: string };

const iso = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
const dmy = (s: string) => (s ? `${s.slice(8, 10)}/${s.slice(5, 7)}/${s.slice(0, 4)}` : "");

export function atajos(hoy = new Date()): { id: string; label: string; rango: Rango }[] {
  const y = hoy.getFullYear(), m = hoy.getMonth();
  const camp = m >= 6 ? y : y - 1; // la campaña empieza el 1 de julio
  return [
    { id: "mes", label: "Este mes", rango: { desde: iso(new Date(y, m, 1)), hasta: iso(new Date(y, m + 1, 0)) } },
    { id: "mes-pasado", label: "Mes pasado", rango: { desde: iso(new Date(y, m - 1, 1)), hasta: iso(new Date(y, m, 0)) } },
    { id: "90", label: "Últimos 90 días", rango: { desde: iso(new Date(y, m, hoy.getDate() - 90)), hasta: iso(hoy) } },
    { id: "campania", label: `Campaña ${camp}/${camp + 1}`, rango: { desde: `${camp}-07-01`, hasta: `${camp + 1}-06-30` } },
    { id: "campania-anterior", label: `Campaña ${camp - 1}/${camp}`, rango: { desde: `${camp - 1}-07-01`, hasta: `${camp}-06-30` } },
    { id: "anio", label: `Año ${y}`, rango: { desde: `${y}-01-01`, hasta: `${y}-12-31` } },
  ];
}

export function etiquetaRango(r: Rango, hoy = new Date()): string {
  if (!r.desde && !r.hasta) return "Todas las fechas";
  const a = atajos(hoy).find((x) => x.rango.desde === r.desde && x.rango.hasta === r.hasta);
  if (a) return a.label;
  if (r.desde && r.hasta) return `${dmy(r.desde)} – ${dmy(r.hasta)}`;
  return r.desde ? `Desde ${dmy(r.desde)}` : `Hasta ${dmy(r.hasta)}`;
}

export function RangoFechas({ valor, onChange, etiqueta = "Fechas" }: { valor: Rango; onChange: (r: Rango) => void; etiqueta?: string }) {
  const [abierto, setAbierto] = useState(false);
  const [libre, setLibre] = useState<Rango>(valor);
  const caja = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!abierto) return;
    const fuera = (e: MouseEvent) => { if (caja.current && !caja.current.contains(e.target as Node)) setAbierto(false); };
    const esc = (e: KeyboardEvent) => { if (e.key === "Escape") setAbierto(false); };
    document.addEventListener("mousedown", fuera); document.addEventListener("keydown", esc);
    return () => { document.removeEventListener("mousedown", fuera); document.removeEventListener("keydown", esc); };
  }, [abierto]);
  const elegir = (r: Rango) => { onChange(r); setAbierto(false); };
  const activo = !!(valor.desde || valor.hasta);

  return (
    <div className="relative" ref={caja}>
      {etiqueta && <span className="mb-1 block text-xs font-medium text-ink-secondary">{etiqueta}</span>}
      <button type="button" onClick={() => { setLibre(valor); setAbierto((v) => !v); }} aria-haspopup="dialog" aria-expanded={abierto}
        className={`inline-flex items-center gap-2 rounded-md border px-3 py-1.5 text-sm transition-colors ${activo ? "border-finance/40 bg-finance-light text-finance" : "border-border bg-surface text-ink-primary hover:bg-surface-sunken"}`}>
        <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={1.8} aria-hidden><rect x="3.5" y="5" width="17" height="15" rx="2" /><path d="M3.5 9.5h17M8 3v4M16 3v4" /></svg>
        {etiquetaRango(valor)}
        <span aria-hidden className="text-ink-muted">▾</span>
      </button>
      <Flotante ancla={caja} abierto={!!(abierto)} className="w-[22rem] rounded-lg border border-border bg-surface p-2 shadow-lg">
<div role="dialog" aria-label="Elegir fechas" >
          <ul className="space-y-0.5">
            {atajos().map((a) => (
              <li key={a.id}>
                <button type="button" onClick={() => elegir(a.rango)}
                  className="flex w-full justify-between rounded-md px-2.5 py-1.5 text-left text-sm hover:bg-surface-sunken">
                  <span>{a.label}</span><span className="text-xs text-ink-muted">{dmy(a.rango.desde).slice(0, 5)} – {dmy(a.rango.hasta).slice(0, 5)}</span>
                </button>
              </li>
            ))}
            <li><button type="button" onClick={() => elegir({ desde: "", hasta: "" })} className="w-full rounded-md px-2.5 py-1.5 text-left text-sm hover:bg-surface-sunken">Todas las fechas</button></li>
          </ul>
          <div className="mt-2 border-t border-border pt-2">
            <p className="mb-1 px-1 text-xs font-medium text-ink-secondary">Rango libre</p>
            <div className="flex items-center gap-2 px-1">
              <input type="date" aria-label="Desde" className="min-w-0 flex-1 rounded-md border border-border px-2 py-1 text-sm" value={libre.desde} onChange={(e) => setLibre((l) => ({ ...l, desde: e.target.value }))} />
              <span className="text-ink-muted">–</span>
              <input type="date" aria-label="Hasta" className="min-w-0 flex-1 rounded-md border border-border px-2 py-1 text-sm" value={libre.hasta} onChange={(e) => setLibre((l) => ({ ...l, hasta: e.target.value }))} />
            </div>
            <div className="mt-2 flex justify-end px-1">
              <button type="button" onClick={() => elegir(libre)} className="rounded-md bg-finance px-3 py-1 text-xs font-medium text-white hover:bg-finance/90">Aplicar</button>
            </div>
          </div>
        </div>
</Flotante>
    </div>
  );
}
