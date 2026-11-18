"use client";
import Link from "next/link";
import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { SoloLectura } from "@/components/auth/SoloLectura";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { formatCantidad, formatFecha } from "@/lib/format";
import { fetchPlanillaMatias, leerPlanillaMatias, type LecturaPlanillaMatias } from "@/services/ordenesApi";

const CULTIVO: Record<string, string> = {
  G: "Girasol", GR: "Girasol", T: "Trigo", S1: "Soja 1ª", S2: "Soja 2ª", M: "Maíz", M1: "Maíz", MZDIF: "Maíz diferido",
  AV: "Avena", PAST: "Pastura",
};
const MOMENTO: [RegExp, string][] = [
  [/^PREM/, "preemergencia"], [/^POST/, "post-emergencia"], [/^FUNGI/, "fungicida"], [/^RESID/, "residual"],
  [/^GRAMI/, "graminicida"], [/^INSECT/, "insecticida"], [/^BCHO/, "barbecho"],
];

/** "G Post" → "Girasol · post-emergencia"; "MzDif prem" → "Maíz diferido · preemergencia". */
export function momentoLegible(m: string): string {
  const s = m.trim().toUpperCase().replace(/\s+/g, " ");
  const k = Object.keys(CULTIVO).sort((a, b) => b.length - a.length).find(c => s.replace(/ /g, "").startsWith(c));
  if (!k) return m;
  const resto = s.replace(/ /g, "").slice(k.length);
  const tipo = MOMENTO.find(([re]) => re.test(resto));
  const nro = resto.match(/(\d+)$/)?.[1];
  return `${CULTIVO[k]}${tipo ? ` · ${tipo[1]}${nro ? ` ${nro}` : ""}` : ""}`;
}

function Momentos({ lista }: { lista?: string[] }) {
  return <div className="flex flex-wrap gap-1.5">{(lista ?? []).map(m => <span key={m} className="rounded-sm bg-agro-light px-2 py-0.5 text-xs font-medium text-agro">{momentoLegible(m)}</span>)}</div>;
}

function Tarjeta({ fecha, estado, tono, momentos, children }: { fecha: string; estado: string; tono: "success" | "warning" | "danger" | "neutral"; momentos?: string[]; children?: React.ReactNode }) {
  const borde = { success: "border-l-status-success", warning: "border-l-status-warning", danger: "border-l-status-danger", neutral: "border-l-border-strong" }[tono];
  return <article className={`rounded-md border border-border border-l-4 ${borde} bg-surface p-4 shadow-sm`}>
    <header className="flex flex-wrap items-center justify-between gap-2">
      <div className="space-y-1.5">
        <h3 className="text-sm font-semibold text-ink-primary">Orden de pulverización del {formatFecha(fecha)}</h3>
        <Momentos lista={momentos} />
      </div>
      <StatusBadge label={estado} tone={tono} />
    </header>
    {children && <div className="mt-3 text-sm text-ink-secondary">{children}</div>}
  </article>;
}

/** 18/11/2026: órdenes de pulverización de la planilla de Matías (solapa "orden pulv LH"). Se lee a pedido, cuando
 * Matías manda la orden por WhatsApp. Las nuevas se crean Planificadas con los productos del stock elegidos por FIFO. */
export function PlanillaMatias() {
  const qc = useQueryClient();
  const [ocupado, setOcupado] = useState(false);
  const [error, setError] = useState("");
  const { data } = useQuery({ queryKey: ["planilla-matias"], queryFn: fetchPlanillaMatias });

  async function leer() {
    setOcupado(true); setError("");
    try {
      qc.setQueryData<LecturaPlanillaMatias>(["planilla-matias"], await leerPlanillaMatias());
      await qc.invalidateQueries({ queryKey: ["ordenes"] });
    } catch (e) { setError(e instanceof Error ? e.message : "No se pudo leer la planilla"); }
    finally { setOcupado(false); }
  }

  const creadas = data?.creadas ?? [], revisar = data?.paraRevisar ?? [], cambiadas = data?.cambiadas ?? [];
  const nada = data?.leida && !creadas.length && !revisar.length && !cambiadas.length;

  return <section className="mb-4 rounded-lg border border-border bg-surface-sunken/60 p-4">
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h2 className="text-base font-semibold text-ink-primary">Órdenes de Matías</h2>
        <p className="text-sm text-ink-secondary">
          Cuando Matías mande la orden por WhatsApp, leé la planilla: la orden se carga planificada con los productos del depósito.
          {data?.leida && <span className="text-ink-muted"> Última lectura: {formatFecha(data.leida)}, {data.leida.slice(11, 16)} h.</span>}
        </p>
      </div>
      <SoloLectura>
        <button onClick={leer} disabled={ocupado}
          className="rounded-md bg-agro px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-agro/90 disabled:opacity-60">
          {ocupado ? "Leyendo la planilla…" : "Leer la planilla de Matías"}
        </button>
      </SoloLectura>
    </div>

    {(creadas.length > 0 || revisar.length > 0 || cambiadas.length > 0) && <div className="mt-4 grid gap-3 lg:grid-cols-2">
      {creadas.map(c => <Tarjeta key={c.fecha} fecha={c.fecha} momentos={c.momentos} estado={c.faltantes.length ? "Cargada · falta stock" : "Cargada"} tono={c.faltantes.length ? "warning" : "success"}>
        {c.idOrden && <p>Quedó como <Link className="font-medium text-finance underline" href={`/produccion/ordenes/${c.idOrden}/editar`}>orden {c.idOrden}</Link>, planificada.</p>}
        {c.faltantes.length > 0 && <div className="mt-2">
          <p className="font-medium text-status-warning">Hay que comprar antes de aplicar:</p>
          <ul className="mt-1 space-y-0.5">{c.faltantes.map(f => <li key={f.producto} className="flex justify-between gap-4 border-b border-border/60 py-0.5 last:border-0">
            <span>{f.producto}</span><span className="font-data tabular-nums">{formatCantidad(f.falta)} {f.unidad?.toLowerCase() ?? ""}</span></li>)}</ul>
        </div>}
      </Tarjeta>)}
      {revisar.map(r => <Tarjeta key={r.fecha} fecha={r.fecha} momentos={r.momentos} estado="Para corregir en la planilla" tono="danger">
        <p className="mb-2">No se cargó: la planilla tiene datos que no cierran. Cuando Matías los corrija, volvé a leerla.</p>
        <ul className="space-y-1.5">{r.problemas.map(p => <li key={p} className="flex gap-2"><span aria-hidden className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-status-danger" /><span>{p}</span></li>)}</ul>
      </Tarjeta>)}
      {cambiadas.map(c => <Tarjeta key={c.fecha} fecha={c.fecha} estado="Cambió en la planilla" tono="neutral">
        <p>Matías la modificó después de cargarla como <Link className="font-medium text-finance underline" href={`/produccion/ordenes/${c.idOrden}/editar`}>orden {c.idOrden}</Link>. Revisá si hay que ajustarla.</p>
      </Tarjeta>)}
    </div>}
    {nada && <p className="mt-3 text-sm text-ink-secondary">No hay órdenes nuevas en la planilla: todas ya están cargadas.</p>}
    {error && <p role="alert" className="mt-3 rounded-md bg-status-danger-bg px-3 py-2 text-sm text-status-danger">{error}</p>}
  </section>;
}
