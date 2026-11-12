"use client";

import { useQuery } from "@tanstack/react-query";

import { CultivoChip } from "@/components/cultivos/CultivoChip";
import { formatMoneda } from "@/lib/format";
import { fetchCatalogosOrdenes } from "@/services/ordenesApi";
import { type CostoDirecto, fetchCampaniasDeCultivo, type ParMonto } from "@/services/resultadoCultivoApi";

/** Piezas comunes de los formularios con el diseño de Access (FrmCostos / FrmResultados). */

export const ar = (v: number | null | undefined) => (v == null ? "—" : formatMoneda(v, "Pesos"));
export const us = (v: number | null | undefined) => (v == null ? "—" : formatMoneda(v, "Dolares"));
export const celdaNum = "whitespace-nowrap px-2 py-1 text-right tabular-nums";

/** Fila de encabezado de Access: combos Cultivo y Campaña (la campaña depende del cultivo) y datos a la derecha. */
export function SelectorCultivoCampania({ idCultivo, idCampania, onCultivo, onCampania, children }: {
  idCultivo: number | null; idCampania: number | null;
  onCultivo: (id: number | null) => void; onCampania: (id: number | null) => void;
  children?: React.ReactNode;
}) {
  const { data: catalogos } = useQuery({ queryKey: ["ordenes", "catalogos"], queryFn: fetchCatalogosOrdenes });
  const { data: campanias } = useQuery({
    queryKey: ["access-campanias", idCultivo], queryFn: () => fetchCampaniasDeCultivo(idCultivo as number), enabled: idCultivo !== null,
  });
  const sel = "ml-2 rounded-sm border border-border bg-surface px-2 py-1 text-sm";
  return (
    <div className="flex flex-wrap items-center gap-x-6 gap-y-2 rounded-md border border-border bg-surface-sunken px-3 py-2 text-sm">
      <label className="font-medium">Cultivo
        <select className={sel} value={idCultivo ?? ""} onChange={(e) => { onCultivo(Number(e.target.value) || null); onCampania(null); }}>
          <option value="">Elegí…</option>
          {catalogos?.cultivos.filter((c) => !/sin cultivo/i.test(c.nombre)).map((c) => <option key={c.idCultivo} value={c.idCultivo}>{c.nombre}</option>)}
        </select>
      </label>
      <label className="font-medium">Campaña
        <select className={sel} value={idCampania ?? ""} disabled={!idCultivo} onChange={(e) => onCampania(Number(e.target.value) || null)}>
          <option value="">Elegí…</option>
          {campanias?.map((c) => <option key={c.idCampania} value={c.idCampania}>{c.campania}</option>)}
        </select>
      </label>
      {children}
    </div>
  );
}

export function Dato({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-3 py-0.5">
      <span className="text-ink-secondary">{label}</span>
      <span className="font-medium tabular-nums">{children}</span>
    </div>
  );
}

export function Titulo({ cultivo, campania }: { cultivo: string; campania: string }) {
  return <p className="flex items-center gap-2 text-sm"><CultivoChip cultivo={cultivo} /><span className="font-medium">{campania}</span></p>;
}

/** Tabla "Costos Directos" de Access (Concepto, AR$, US$, AR$/HA, US$/HA) con sus filas de totales. */
export function TablaCostosDirectos({ filas, totales, seleccionado, onConcepto }: {
  filas: CostoDirecto[];
  totales: { label: string; monto: ParMonto | undefined; sinHa?: boolean; fuerte?: boolean }[];
  seleccionado?: number | null;
  onConcepto?: (f: CostoDirecto) => void;
}) {
  return (
    <section className="rounded-md border border-border bg-surface">
      <h3 className="border-b border-border bg-surface-sunken px-3 py-1.5 text-sm font-semibold">Costos Directos</h3>
      <table className="w-full text-sm">
        <thead className="text-xs text-ink-secondary">
          <tr className="border-b border-border">
            <th className="px-2 py-1 text-left font-medium">Concepto</th>
            <th className="px-2 py-1 text-right font-medium">AR$</th>
            <th className="px-2 py-1 text-right font-medium">US$</th>
            <th className="px-2 py-1 text-right font-medium">AR$ / HA</th>
            <th className="px-2 py-1 text-right font-medium">US$ / HA</th>
          </tr>
        </thead>
        <tbody>
          {filas.map((f) => (
            <tr key={f.idRubro} onClick={onConcepto ? () => onConcepto(f) : undefined}
              className={`border-b border-border ${onConcepto ? "cursor-pointer hover:bg-surface-sunken" : ""} ${seleccionado === f.idRubro ? "bg-amber-50" : ""}`}>
              <td className="px-2 py-1">{f.concepto}</td>
              <td className={celdaNum}>{ar(f.pesos)}</td>
              <td className={celdaNum}>{us(f.dolares)}</td>
              <td className={celdaNum}>{ar(f.haPesos)}</td>
              <td className={celdaNum}>{us(f.haDolares)}</td>
            </tr>
          ))}
          {filas.length === 0 && <tr><td colSpan={5} className="px-2 py-3 text-center text-ink-secondary">Sin costos cargados.</td></tr>}
        </tbody>
        <tfoot>
          {totales.map((t, i) => (
            <tr key={t.label} className={`${i === 0 ? "border-t-2 border-ink-secondary/40" : "border-t border-border"} ${t.fuerte ? "bg-surface-sunken font-semibold" : ""}`}>
              <td className="px-2 py-1">{t.label}</td>
              <td className={celdaNum}>{ar(t.monto?.pesos)}</td>
              <td className={celdaNum}>{us(t.monto?.dolares)}</td>
              <td className={celdaNum}>{t.sinHa ? "" : ar(t.monto?.haPesos)}</td>
              <td className={celdaNum}>{t.sinHa ? "" : us(t.monto?.haDolares)}</td>
            </tr>
          ))}
        </tfoot>
      </table>
    </section>
  );
}
