"use client";

import { Fragment, useMemo, useState } from "react";

import { SideDrawer } from "@/components/ui/SideDrawer";
import { useToast } from "@/components/ui/Toast";
import { formatCantidad } from "@/lib/format";
import { ApiError } from "@/services/apiClient";
import type { Campania, Cultivo, Lote } from "@/services/ordenesApi";
import { crearPlanAgricola, eliminarPlanAgricola, type PlanAgricolaItem } from "@/services/planificacionApi";

import { anioAgricola, colorCultivo, LOTES_PLANO, lotePlano } from "./lotesPlano";

const VISIBLES = 6;
const etiquetaAnio = (a: number) => `${String(a).slice(2)}/${String(a + 1).slice(2)}`;

/**
 * Planificación agrícola como grilla lote × año agrícola (12/11/2026): cada fila es un lote del plano (con sus
 * subdivisiones plegables) y cada columna un año, con la campaña fina arriba y la gruesa abajo. Un clic en la celda
 * abre el panel para asignar o quitar cultivos y ver la rotación del lote.
 */
export function PlanificacionAgricolaListado({
  items, lotes, cultivos, campanias, onCambio,
}: {
  items: PlanAgricolaItem[];
  lotes: Lote[];
  cultivos: Cultivo[];
  campanias: Campania[];
  onCambio: () => void;
}) {
  const { showToast } = useToast();
  const lotesValidos = useMemo(() => lotes.filter((l) => l.numeroLote !== "PRUE"), [lotes]);

  const anios = useMemo(() => {
    const s = new Set<number>();
    for (const c of campanias) { const a = anioAgricola(c.nombre); if (a) s.add(a.anio); }
    return [...s].sort((a, b) => a - b);
  }, [campanias]);
  const ultimoConPlan = useMemo(() => {
    let m = 0;
    for (const i of items) { const a = anioAgricola(i.campania ?? ""); if (a && a.anio > m) m = a.anio; }
    return m || anios[anios.length - 1];
  }, [items, anios]);
  const [hasta, setHasta] = useState<number>(Math.max(0, anios.indexOf(ultimoConPlan)));
  const desde = Math.max(0, hasta - VISIBLES + 1);
  const visibles = anios.slice(desde, hasta + 1);

  const [abiertos, setAbiertos] = useState<Record<string, boolean>>({});
  const [celda, setCelda] = useState<{ idLote: number | null; plano: string; anio: number } | null>(null);

  // Filas: lote del plano → lotes del sistema que caen en él.
  const filas = useMemo(() => {
    const porPlano = new Map<string, Lote[]>();
    const sinPlano: Lote[] = [];
    for (const l of lotesValidos) {
      const p = lotePlano(l.numeroLote);
      if (!p) sinPlano.push(l);
      else porPlano.set(p, [...(porPlano.get(p) ?? []), l]);
    }
    return { porPlano, sinPlano };
  }, [lotesValidos]);

  const enCelda = (idsLote: number[], anio: number) =>
    items
      .filter((i) => idsLote.includes(i.idLote) && anioAgricola(i.campania ?? "")?.anio === anio)
      .sort((a, b) => Number(anioAgricola(b.campania ?? "")?.fina) - Number(anioAgricola(a.campania ?? "")?.fina));

  const totales = useMemo(() => {
    const t = new Map<number, Map<string, number>>();
    for (const i of items) {
      const a = anioAgricola(i.campania ?? "");
      if (!a) continue;
      const m = t.get(a.anio) ?? new Map<string, number>();
      m.set(i.cultivo ?? "—", (m.get(i.cultivo ?? "—") ?? 0) + (i.superficie ?? 0));
      t.set(a.anio, m);
    }
    return t;
  }, [items]);

  function Chips({ lista }: { lista: PlanAgricolaItem[] }) {
    if (!lista.length) return <span className="text-ink-muted">·</span>;
    return (
      <div className="flex flex-col gap-0.5">
        {lista.map((i) => (
          <span key={i.idPlanAgricola} title={`${i.cultivo} · ${i.campania} · lote ${i.numeroLote}`}
            className={`truncate rounded-sm border px-1.5 text-xs leading-5 ${colorCultivo(i.cultivo)}`}>
            {i.cultivo}
          </span>
        ))}
      </div>
    );
  }

  function Fila({ etiqueta, ha, idsLote, plano, idLote, sub, plegable }: {
    etiqueta: string; ha: number; idsLote: number[]; plano: string; idLote: number | null; sub?: boolean; plegable?: boolean;
  }) {
    return (
      <tr className="border-b border-border">
        <th scope="row" className={`sticky left-0 z-[1] whitespace-nowrap bg-surface py-1 pr-2 text-left font-medium ${sub ? "pl-6 text-ink-secondary" : "pl-1"}`}>
          {plegable ? (
            <button type="button" className="mr-1 text-ink-secondary" aria-expanded={!!abiertos[plano]}
              aria-label={`${abiertos[plano] ? "Plegar" : "Desplegar"} subdivisiones del lote ${etiqueta}`}
              onClick={() => setAbiertos({ ...abiertos, [plano]: !abiertos[plano] })}>{abiertos[plano] ? "▾" : "▸"}</button>
          ) : !sub && <span className="mr-1 inline-block w-3" />}
          {etiqueta}
        </th>
        <td className="whitespace-nowrap px-2 py-1 text-right text-ink-secondary">{formatCantidad(ha)}</td>
        {visibles.map((a) => (
          <td key={a} className="p-0.5 align-top">
            <button type="button" onClick={() => setCelda({ idLote, plano, anio: a })}
              className="block min-h-[1.75rem] w-full rounded-sm p-0.5 text-left hover:bg-surface-sunken focus:outline-none focus:ring-2 focus:ring-agro"
              aria-label={`Lote ${etiqueta}, campaña ${etiquetaAnio(a)}`}>
              <Chips lista={enCelda(idsLote, a)} />
            </button>
          </td>
        ))}
      </tr>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <button type="button" className="rounded-sm border border-border px-2 py-1 disabled:opacity-40" disabled={desde === 0}
          onClick={() => setHasta(hasta - 1)} aria-label="Campaña anterior">←</button>
        <span>Campañas {etiquetaAnio(visibles[0] ?? 0)} a {etiquetaAnio(visibles[visibles.length - 1] ?? 0)}</span>
        <button type="button" className="rounded-sm border border-border px-2 py-1 disabled:opacity-40" disabled={hasta >= anios.length - 1}
          onClick={() => setHasta(hasta + 1)} aria-label="Campaña siguiente">→</button>
        <span className="ml-2 text-ink-secondary">En cada celda: arriba la campaña fina, abajo la gruesa. Clic para asignar o quitar.</span>
      </div>

      <div className="overflow-x-auto rounded-sm border border-border">
        <table className="w-full table-fixed text-sm">
          <colgroup><col className="w-24" /><col className="w-16" />{visibles.map((a) => <col key={a} />)}</colgroup>
          <thead className="bg-surface-sunken text-xs text-ink-secondary">
            <tr>
              <th className="sticky left-0 bg-surface-sunken px-1 py-1.5 text-left">Lote</th>
              <th className="px-2 py-1.5 text-right">ha</th>
              {visibles.map((a) => <th key={a} className="px-1 py-1.5 text-left">{etiquetaAnio(a)}</th>)}
            </tr>
          </thead>
          <tbody>
            {LOTES_PLANO.map((p) => {
              const propios = filas.porPlano.get(p.id) ?? [];
              const ids = propios.map((l) => l.idLote);
              const principal = propios.find((l) => l.numeroLote === p.id) ?? null;
              const subs = propios.filter((l) => l !== principal);
              return (
                <Fragment key={p.id}>
                  <Fila etiqueta={p.nombre} ha={p.ha} idsLote={ids} plano={p.id} idLote={principal?.idLote ?? null} plegable={subs.length > 0} />
                  {abiertos[p.id] && subs.map((l) => (
                    <Fila key={l.idLote} etiqueta={l.numeroLote} ha={l.superficie} idsLote={[l.idLote]} plano={p.id} idLote={l.idLote} sub />
                  ))}
                </Fragment>
              );
            })}
            {filas.sinPlano.map((l) => (
              <Fila key={l.idLote} etiqueta={l.numeroLote} ha={l.superficie} idsLote={[l.idLote]} plano={l.numeroLote} idLote={l.idLote} />
            ))}
          </tbody>
          <tfoot className="bg-surface-sunken text-xs">
            <tr>
              <th className="sticky left-0 bg-surface-sunken px-1 py-1.5 text-left align-top">Total ha</th>
              <td />
              {visibles.map((a) => (
                <td key={a} className="px-1 py-1.5 align-top">
                  {[...(totales.get(a) ?? new Map()).entries()].sort((x, y) => y[1] - x[1]).map(([c, ha]) => (
                    <div key={c} className="flex justify-between gap-1"><span className="truncate">{c}</span><span>{formatCantidad(ha)}</span></div>
                  ))}
                </td>
              ))}
            </tr>
          </tfoot>
        </table>
      </div>

      {celda && (
        <PanelCelda celda={celda} lotes={lotesValidos} cultivos={cultivos} campanias={campanias} items={items}
          onClose={() => setCelda(null)}
          onCrear={async (d) => {
            try { await crearPlanAgricola(d); showToast("Lote asignado.", "success"); onCambio(); }
            catch (e) { showToast(e instanceof ApiError ? e.message : "No se pudo asignar el lote.", "danger"); }
          }}
          onQuitar={async (id) => {
            try { await eliminarPlanAgricola(id); showToast("Asignación eliminada.", "success"); onCambio(); }
            catch (e) { showToast(e instanceof ApiError ? e.message : "No se pudo eliminar.", "danger"); }
          }} />
      )}
    </div>
  );
}

function PanelCelda({ celda, lotes, cultivos, campanias, items, onClose, onCrear, onQuitar }: {
  celda: { idLote: number | null; plano: string; anio: number };
  lotes: Lote[]; cultivos: Cultivo[]; campanias: Campania[]; items: PlanAgricolaItem[];
  onClose: () => void;
  onCrear: (d: { idLote: number; idCultivo: number; idCampania: number }) => Promise<void>;
  onQuitar: (id: number) => Promise<void>;
}) {
  const delPlano = lotes.filter((l) => (lotePlano(l.numeroLote) ?? l.numeroLote) === celda.plano);
  const delAnio = campanias.filter((c) => anioAgricola(c.nombre)?.anio === celda.anio)
    .sort((a, b) => Number(anioAgricola(b.nombre)?.fina) - Number(anioAgricola(a.nombre)?.fina));
  const [idLote, setIdLote] = useState<number | null>(celda.idLote ?? delPlano[0]?.idLote ?? null);
  const [idCampania, setIdCampania] = useState<number | null>(delAnio[delAnio.length - 1]?.idCampania ?? null);
  const [idCultivo, setIdCultivo] = useState<number | null>(null);
  const [guardando, setGuardando] = useState(false);
  const ids = delPlano.map((l) => l.idLote);
  const asignados = items.filter((i) => ids.includes(i.idLote) && anioAgricola(i.campania ?? "")?.anio === celda.anio);
  const historia = items.filter((i) => ids.includes(i.idLote))
    .sort((a, b) => (b.campania ?? "").localeCompare(a.campania ?? ""));
  const nombre = LOTES_PLANO.find((p) => p.id === celda.plano)?.nombre ?? celda.plano;
  const sel = "mt-1 block w-full rounded-sm border border-border bg-surface px-2 py-1.5 text-sm";

  return (
    <SideDrawer open onClose={onClose} title={`Lote ${nombre} · campaña ${etiquetaAnio(celda.anio)}`}>
      <div className="space-y-5 text-sm">
        <section>
          <h3 className="mb-2 font-medium">Asignado en esta campaña</h3>
          {asignados.length === 0 && <p className="text-ink-secondary">Nada asignado.</p>}
          <ul className="space-y-1">
            {asignados.map((i) => (
              <li key={i.idPlanAgricola} className="flex items-center justify-between gap-2">
                <span><span className={`rounded-sm border px-1.5 ${colorCultivo(i.cultivo)}`}>{i.cultivo}</span>
                  <span className="ml-2 text-ink-secondary">{i.campania} · lote {i.numeroLote} · {formatCantidad(i.superficie ?? 0)} ha</span></span>
                <button type="button" className="text-status-danger hover:underline" onClick={() => onQuitar(i.idPlanAgricola)}>Quitar</button>
              </li>
            ))}
          </ul>
        </section>

        <section className="rounded-sm border border-border p-3">
          <h3 className="mb-2 font-medium">Asignar cultivo</h3>
          <div className="grid grid-cols-3 gap-2">
            <label>Lote<select className={sel} value={idLote ?? ""} onChange={(e) => setIdLote(Number(e.target.value) || null)}>
              {delPlano.map((l) => <option key={l.idLote} value={l.idLote}>{l.numeroLote} ({formatCantidad(l.superficie)} ha)</option>)}
            </select></label>
            <label>Campaña<select className={sel} value={idCampania ?? ""} onChange={(e) => setIdCampania(Number(e.target.value) || null)}>
              {delAnio.map((c) => <option key={c.idCampania} value={c.idCampania}>{c.nombre} ({anioAgricola(c.nombre)?.fina ? "fina" : "gruesa"})</option>)}
            </select></label>
            <label>Cultivo<select className={sel} value={idCultivo ?? ""} onChange={(e) => setIdCultivo(Number(e.target.value) || null)}>
              <option value="">Elegí…</option>
              {cultivos.map((c) => <option key={c.idCultivo} value={c.idCultivo}>{c.nombre}</option>)}
            </select></label>
          </div>
          {delAnio.length === 0 && <p className="mt-2 text-status-warning">Esta campaña no existe todavía en el sistema.</p>}
          <div className="mt-3 flex justify-end">
            <button type="button" disabled={guardando || !idLote || !idCampania || !idCultivo}
              className="rounded-sm bg-agro px-3 py-1.5 text-white disabled:opacity-50"
              onClick={async () => { setGuardando(true); await onCrear({ idLote: idLote!, idCultivo: idCultivo!, idCampania: idCampania! }); setIdCultivo(null); setGuardando(false); }}>
              Asignar
            </button>
          </div>
        </section>

        <section>
          <h3 className="mb-2 font-medium">Rotación del lote</h3>
          {historia.length === 0 && <p className="text-ink-secondary">Sin historia cargada.</p>}
          <table className="w-full">
            <tbody>
              {historia.map((i) => (
                <tr key={i.idPlanAgricola} className="border-b border-border">
                  <td className="py-0.5 pr-2 text-ink-secondary">{i.campania}</td>
                  <td className="py-0.5 pr-2">{i.numeroLote}</td>
                  <td className="py-0.5"><span className={`rounded-sm border px-1.5 text-xs ${colorCultivo(i.cultivo)}`}>{i.cultivo}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      </div>
    </SideDrawer>
  );
}
