"use client";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { Segmentos } from "@/components/ui/Segmentos";
import { SideDrawer } from "@/components/ui/SideDrawer";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/States";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { TiraIndicadores } from "@/components/ui/TiraIndicadores";
import { formatCantidad, formatFecha, formatMoneda } from "@/lib/format";
import { apiGet } from "@/services/apiClient";

/** Inversiones (plazos fijos y FCI Fima), 19/11/2026 — diseño specs/051-experiencia-uso-moderna/diseno-inversiones-20261119.md.
 * Solo lectura: el capital es un pase entre el banco y la inversión; solo el rendimiento es resultado ("Resultados
 * financieros", Adm. General), por ejercicio del 01/04 al 31/03. */
interface PlazoFijo { cuenta: string; constitucion: string; capital: number; vencimiento: string | null; cobrado: number | null; rendimiento: number | null; dias: number | null; tna: number | null; estado: "vigente" | "cobrado" | "revisar" }
interface MesFima { periodo: string; fecha: string; saldoAnterior: number; suscripciones: number; rescates: number; saldo: number; rendimiento: number }
interface Ejercicio { ejercicio: string; plazoFijoNacion: number; plazoFijoGalicia: number; fima: number; total: number }
interface Resumen {
  invertido: number; fimaSaldo: number; fimaFecha: string | null; rendimientoEjercicio: number; ejercicioActual: string;
  plazosFijosVigentes: PlazoFijo[]; revisar: PlazoFijo[]; plazosFijos: PlazoFijo[]; fima: MesFima[]; ejercicios: Ejercicio[];
}
type Vista = "rendimiento" | "plazos" | "fima" | "revisar";
const MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];
const mesTexto = (p: string) => `${MESES[Number(p.slice(5, 7)) - 1]} ${p.slice(0, 4)}`;

function Barras({ ejercicios }: { ejercicios: Ejercicio[] }) {
  const max = Math.max(1, ...ejercicios.map((e) => e.total));
  const partes: [keyof Ejercicio, string, string][] = [["plazoFijoNacion", "Plazo fijo Nación", "bg-finance/70"], ["plazoFijoGalicia", "Plazo fijo Galicia", "bg-agro/60"], ["fima", "Fondo Fima", "bg-amber-400/80"]];
  return (
    <div className="rounded-lg border border-border bg-surface p-4">
      <div className="mb-3 flex flex-wrap gap-4 text-xs text-ink-secondary">
        {partes.map(([, n, c]) => <span key={n} className="inline-flex items-center gap-1.5"><span className={`h-2.5 w-2.5 rounded-sm ${c}`} />{n}</span>)}
      </div>
      <div className="flex h-40 items-end gap-3">
        {ejercicios.map((e) => (
          <div key={e.ejercicio} className="flex flex-1 flex-col items-center gap-1" title={`${e.ejercicio}: ${formatMoneda(e.total)}`}>
            <span className="font-data text-[11px] text-ink-secondary">{formatMoneda(e.total).replace(/,\d\d$/, "")}</span>
            <div className="flex w-full max-w-[3rem] flex-col-reverse overflow-hidden rounded-t" style={{ height: `${Math.max(2, (e.total / max) * 120)}px` }}>
              {partes.map(([k, n, c]) => { const v = e[k] as number; return v > 0 ? <div key={n} className={c} style={{ height: `${(v / e.total) * 100}%` }} /> : null; })}
            </div>
            <span className="text-[11px] text-ink-secondary">{e.ejercicio}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export function Inversiones() {
  const q = useQuery({ queryKey: ["tesoreria-inversiones"], queryFn: () => apiGet<Resumen>("/api/tesoreria/inversiones") });
  const [vista, setVista] = useState<Vista>("rendimiento");
  const [pf, setPf] = useState<PlazoFijo | null>(null);
  const [mes, setMes] = useState<MesFima | null>(null);
  if (q.isLoading) return <LoadingState rows={6} />;
  if (q.isError || !q.data) return <ErrorState message="No se pudieron leer las inversiones." onRetry={() => q.refetch()} />;
  const d = q.data;

  const colPf: DataTableColumn<PlazoFijo>[] = [
    { key: "cuenta", header: "Cuenta", render: (p) => p.cuenta },
    { key: "constitucion", header: "Constitución", render: (p) => formatFecha(p.constitucion) },
    { key: "capital", header: "Capital", numeric: true, align: "right", render: (p) => formatMoneda(p.capital) },
    { key: "vencimiento", header: "Cobro", render: (p) => (p.vencimiento ? formatFecha(p.vencimiento) : "—") },
    { key: "dias", header: "Días", numeric: true, align: "right", render: (p) => (p.dias != null ? formatCantidad(p.dias) : "—") },
    { key: "rendimiento", header: "Rendimiento", numeric: true, align: "right", render: (p) => (p.rendimiento != null ? formatMoneda(p.rendimiento) : "—") },
    { key: "estado", header: "Estado", render: (p) => <StatusBadge label={p.estado === "cobrado" ? "Cobrado" : p.estado === "vigente" ? "Vigente" : "Revisar"} tone={p.estado === "cobrado" ? "success" : "warning"} /> },
  ];
  const colFima: DataTableColumn<MesFima>[] = [
    { key: "periodo", header: "Mes", render: (m) => mesTexto(m.periodo) },
    { key: "suscripciones", header: "Suscripciones", numeric: true, align: "right", render: (m) => (m.suscripciones ? formatMoneda(m.suscripciones) : "—") },
    { key: "rescates", header: "Rescates", numeric: true, align: "right", render: (m) => (m.rescates ? formatMoneda(m.rescates) : "—") },
    { key: "saldo", header: "Saldo del extracto", numeric: true, align: "right", render: (m) => formatMoneda(m.saldo) },
    { key: "rendimiento", header: "Rendimiento", numeric: true, align: "right", render: (m) => formatMoneda(m.rendimiento) },
  ];

  return (
    <div className="space-y-3">
      <TiraIndicadores items={[
        { titulo: "Invertido hoy", valor: formatMoneda(d.invertido), pie: d.fimaFecha ? `Fima al ${formatFecha(d.fimaFecha)}` : undefined },
        { titulo: `Rendimiento ${d.ejercicioActual}`, valor: formatMoneda(d.rendimientoEjercicio), pie: "01/04 al 31/03" },
        { titulo: "Plazos fijos vigentes", valor: formatCantidad(d.plazosFijosVigentes.length) },
        { titulo: "Para revisar", valor: formatCantidad(d.revisar.length), aviso: d.revisar.length > 0, onClick: d.revisar.length ? () => setVista("revisar") : undefined },
      ]} />

      <Segmentos<Vista> etiqueta="Vista" valor={vista} onChange={setVista} opciones={[
        { id: "rendimiento", label: "Rendimiento por ejercicio" }, { id: "plazos", label: "Plazos fijos" }, { id: "fima", label: "Fondo Fima" },
        ...(d.revisar.length ? [{ id: "revisar" as Vista, label: "Para revisar", aviso: d.revisar.length }] : [])]} />

      {vista === "rendimiento" && (
        <>
          <Barras ejercicios={d.ejercicios} />
          <div className="overflow-hidden rounded-lg border border-border bg-surface">
            <table className="w-full text-sm">
              <thead className="bg-surface-sunken text-xs text-ink-secondary">
                <tr><th className="px-3 py-2 text-left">Ejercicio</th><th className="px-3 py-2 text-right">Plazo fijo Nación</th><th className="px-3 py-2 text-right">Plazo fijo Galicia</th><th className="px-3 py-2 text-right">Fondo Fima</th><th className="px-3 py-2 text-right">Total</th></tr>
              </thead>
              <tbody className="divide-y divide-border">
                {[...d.ejercicios].reverse().map((e) => (
                  <tr key={e.ejercicio}>
                    <td className="px-3 py-1.5">{e.ejercicio}</td>
                    <td className="px-3 py-1.5 text-right font-data">{e.plazoFijoNacion ? formatMoneda(e.plazoFijoNacion) : "—"}</td>
                    <td className="px-3 py-1.5 text-right font-data">{e.plazoFijoGalicia ? formatMoneda(e.plazoFijoGalicia) : "—"}</td>
                    <td className="px-3 py-1.5 text-right font-data">{e.fima ? formatMoneda(e.fima) : "—"}</td>
                    <td className="px-3 py-1.5 text-right font-data font-semibold">{formatMoneda(e.total)}</td>
                  </tr>
                ))}
              </tbody>
              <tfoot className="border-t border-border font-medium">
                <tr><td className="px-3 py-2">Total</td><td /><td /><td />
                  <td className="px-3 py-2 text-right font-data">{formatMoneda(d.ejercicios.reduce((s, e) => s + e.total, 0))}</td></tr>
              </tfoot>
            </table>
          </div>
          <p className="text-xs text-ink-secondary">Solo el rendimiento es resultado de la empresa (Resultados financieros, Adm. General). El capital es un pase entre el banco y la inversión.</p>
        </>
      )}
      {vista === "plazos" && <DataTable columns={colPf} rows={d.plazosFijos} keyField={(p) => `${p.cuenta}-${p.constitucion}-${p.capital}`}
        emptyMessage="No hay plazos fijos." page={1} pageSize={500} total={d.plazosFijos.length} onPageChange={() => {}} onRowClick={setPf} />}
      {vista === "fima" && (d.fima.length ? <DataTable columns={colFima} rows={[...d.fima].reverse()} keyField={(m) => m.periodo}
        emptyMessage="" page={1} pageSize={500} total={d.fima.length} onPageChange={() => {}} onRowClick={setMes} />
        : <EmptyState message="Todavía no hay extractos del Fima." />)}
      {vista === "revisar" && <DataTable columns={colPf} rows={d.revisar} keyField={(p) => `${p.cuenta}-${p.constitucion}`}
        emptyMessage="Nada para revisar." page={1} pageSize={100} total={d.revisar.length} onPageChange={() => {}} onRowClick={setPf} />}

      {pf && (
        <SideDrawer open onClose={() => setPf(null)} title={`${pf.cuenta} · ${formatMoneda(pf.capital)}`} subtitulo={`Constituido el ${formatFecha(pf.constitucion)}`}>
          <dl className="grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
            <dt className="text-ink-secondary">Capital (pase desde el banco)</dt><dd className="text-right font-data">{formatMoneda(pf.capital)}</dd>
            <dt className="text-ink-secondary">Cobrado</dt><dd className="text-right font-data">{pf.cobrado != null ? `${formatMoneda(pf.cobrado)} el ${formatFecha(pf.vencimiento)}` : "todavía no"}</dd>
            <dt className="text-ink-secondary">Rendimiento</dt><dd className="text-right font-data font-semibold">{pf.rendimiento != null ? formatMoneda(pf.rendimiento) : "—"}</dd>
            <dt className="text-ink-secondary">Plazo</dt><dd className="text-right font-data">{pf.dias != null ? `${formatCantidad(pf.dias)} días` : "—"}</dd>
            <dt className="text-ink-secondary">Tasa anual equivalente</dt><dd className="text-right font-data">{pf.tna != null ? `${formatCantidad(pf.tna)} %` : "—"}</dd>
          </dl>
          {pf.dias != null && pf.dias > 60 && <p className="mt-4 text-xs text-ink-secondary">Se renovó al vencimiento con los intereses incluidos; el rendimiento es el de todo el período.</p>}
        </SideDrawer>
      )}
      {mes && (
        <SideDrawer open onClose={() => setMes(null)} title={`Fondo Fima · ${mesTexto(mes.periodo)}`} subtitulo={`Extracto al ${formatFecha(mes.fecha)}`}>
          <dl className="grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
            <dt className="text-ink-secondary">Saldo anterior</dt><dd className="text-right font-data">{formatMoneda(mes.saldoAnterior)}</dd>
            <dt className="text-ink-secondary">+ Suscripciones</dt><dd className="text-right font-data">{formatMoneda(mes.suscripciones)}</dd>
            <dt className="text-ink-secondary">− Rescates</dt><dd className="text-right font-data">{formatMoneda(mes.rescates)}</dd>
            <dt className="text-ink-secondary">Saldo del extracto</dt><dd className="text-right font-data">{formatMoneda(mes.saldo)}</dd>
            <dt className="border-t border-border pt-2 font-medium">Rendimiento del mes</dt><dd className="border-t border-border pt-2 text-right font-data font-semibold">{formatMoneda(mes.rendimiento)}</dd>
          </dl>
        </SideDrawer>
      )}
    </div>
  );
}
