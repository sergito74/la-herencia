"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { SideDrawer } from "@/components/ui/SideDrawer";
import { LoadingState } from "@/components/ui/States";
import { formatFecha, formatMonto, formatNumero } from "@/lib/format";
import {
  fetchDetalleGanadero,
  type MonedaGanaderia,
  type ResultadoGanadero,
  type VistaGanaderia,
} from "@/services/ganaderiaApi";

function Monto({ v, moneda, fuerte }: { v: number | null | undefined; moneda: MonedaGanaderia; fuerte?: boolean }) {
  if (v === null || v === undefined) return <span className="text-ink-muted">—</span>;
  const neg = v < 0;
  return (
    <span className={`font-data ${neg ? "text-status-danger" : ""} ${fuerte ? "font-semibold" : ""}`}>
      {neg ? `(${formatMonto(Math.abs(v), 0)})` : formatMonto(v, 0)}
      <span className="sr-only">{moneda === "USD" ? " dólares" : " pesos"}</span>
    </span>
  );
}

const TOTALES: { clave: keyof ResultadoGanadero["indicadores"][string]; titulo: string; antesDe: string }[] = [
  { clave: "ventasNetas", titulo: "Ventas netas", antesDe: "CompraHacienda" },
  { clave: "ingresoNeto", titulo: "Ingreso neto", antesDe: "Pastaje" },
  { clave: "margenBruto", titulo: "Margen bruto", antesDe: "Estructura" },
];

/** 052 US1: cuadro de resultado ganadero (rubros × períodos), con detalle por celda hasta el comprobante. */
export function CuadroResultado({ datos, vista, establecimiento }: {
  datos: ResultadoGanadero; vista: VistaGanaderia; establecimiento?: number;
}) {
  const [abiertos, setAbiertos] = useState<Record<string, boolean>>({});
  const [celda, setCelda] = useState<{ grupo: string; rubro: string; periodo: string } | null>(null);
  const claves = datos.periodos.map((p) => p.clave);
  const m = datos.moneda;
  const totalGrupo = (grupo: string, periodo: string) =>
    datos.filas.filter((f) => f.grupo === grupo).reduce((s, f) => s + (f.valores[periodo] ?? 0), 0);
  const hayGrupo = (grupo: string) => datos.filas.some((f) => f.grupo === grupo);

  const filasTotal = (antesDe: string) =>
    TOTALES.filter((t) => t.antesDe === antesDe).map((t) => (
      <tr key={t.clave} className="border-t-2 border-border bg-surface-sunken/60">
        <th scope="row" className="sticky left-0 bg-surface-sunken px-3 py-1.5 text-left font-semibold">{t.titulo}</th>
        {claves.map((k) => <td key={k} className="px-3 py-1.5 text-right"><Monto v={datos.indicadores[k]?.[t.clave] as number} moneda={m} fuerte /></td>)}
      </tr>
    ));

  return (
    <div className="overflow-auto rounded-md border border-border bg-surface">
      <table className="min-w-full text-sm">
        <thead className="sticky top-0 z-10 bg-surface">
          <tr className="border-b border-border">
            <th className="sticky left-0 z-20 bg-surface px-3 py-2 text-left font-medium text-ink-secondary">
              {m === "USD" ? "us$" : "$"} · {vista === "ejercicio" ? "Ejercicio (abr–mar)" : "Campaña (jul–jun)"}
            </th>
            {claves.map((k) => <th key={k} className="px-3 py-2 text-right font-medium">{k}</th>)}
          </tr>
        </thead>
        <tbody>
          {datos.grupos.map((g) => {
            const filas = datos.filas.filter((f) => f.grupo === g.grupo);
            const out: React.ReactNode[] = [filasTotal(g.grupo)];
            if (!filas.length && g.grupo !== "Inventario") return out;
            const abierto = abiertos[g.grupo] ?? g.grupo === "Ventas";
            out.push(
              <tr key={g.grupo} className="border-t border-border">
                <th scope="row" className="sticky left-0 bg-surface px-3 py-1.5 text-left font-medium">
                  <button type="button" onClick={() => setAbiertos({ ...abiertos, [g.grupo]: !abierto })}
                    className="inline-flex items-center gap-1 hover:text-finance" aria-expanded={abierto}>
                    <span aria-hidden>{abierto ? "▾" : "▸"}</span>{g.titulo}{g.signo < 0 && hayGrupo(g.grupo) ? " (−)" : ""}
                  </button>
                </th>
                {claves.map((k) => (
                  <td key={k} className="px-3 py-1.5 text-right">
                    {g.grupo === "Inventario" && datos.indicadores[k]?.sinInventario
                      ? <span className="text-xs text-ink-muted">sin stock valuado</span>
                      : <Monto v={filas.length ? totalGrupo(g.grupo, k) : null} moneda={m} />}
                  </td>
                ))}
              </tr>,
            );
            if (abierto) {
              for (const f of filas) {
                out.push(
                  <tr key={`${g.grupo}-${f.rubro}`} className="text-ink-secondary">
                    <th scope="row" className="sticky left-0 bg-surface py-1 pl-8 pr-3 text-left font-normal">{f.rubro}</th>
                    {claves.map((k) => (
                      <td key={k} className="px-3 py-1 text-right">
                        {f.valores[k] !== null && f.valores[k] !== undefined ? (
                          <button type="button" className="hover:underline" title="Ver comprobantes"
                            onClick={() => setCelda({ grupo: f.grupo, rubro: f.rubro, periodo: k })}>
                            <Monto v={f.valores[k]} moneda={m} />
                          </button>
                        ) : <span className="text-ink-muted">—</span>}
                      </td>
                    ))}
                  </tr>,
                );
              }
            }
            return out;
          })}
          <tr className="border-t-2 border-ink-primary/40 bg-surface-sunken">
            <th scope="row" className="sticky left-0 bg-surface-sunken px-3 py-2 text-left font-semibold">Resultado operativo</th>
            {claves.map((k) => <td key={k} className="px-3 py-2 text-right"><Monto v={datos.indicadores[k]?.resultadoOperativo} moneda={m} fuerte /></td>)}
          </tr>
          {([
            ["haGanaderas", "Hectáreas ganaderas", false],
            ["mbHa", "Margen bruto por ha", true],
            ["costoDirectoHa", "Costo directo por ha", true],
            ["kgVendidos", "Kg vendidos", false],
            ["cabezasVendidas", "Cabezas vendidas", false],
            ["kgProducidos", "Kg producidos", false],
            ["costoPorKg", "Costo directo por kg producido", true],
            ["evHa", "Carga (EV/ha)", false],
          ] as const).map(([clave, titulo, esMonto]) => (
            <tr key={clave} className="border-t border-border text-ink-secondary">
              <th scope="row" className="sticky left-0 bg-surface px-3 py-1 text-left font-normal">{titulo}</th>
              {claves.map((k) => {
                const v = datos.indicadores[k]?.[clave] as number | null | undefined;
                return (
                  <td key={k} className="px-3 py-1 text-right font-data">
                    {v === null || v === undefined ? <span className="text-ink-muted">—</span>
                      : esMonto ? <Monto v={v} moneda={m} /> : formatNumero(v, { max: 1 })}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
      {celda && <DetalleCelda celda={celda} vista={vista} moneda={m} establecimiento={establecimiento} onClose={() => setCelda(null)} />}
    </div>
  );
}

function DetalleCelda({ celda, vista, moneda, establecimiento, onClose }: {
  celda: { grupo: string; rubro: string; periodo: string }; vista: VistaGanaderia; moneda: MonedaGanaderia;
  establecimiento?: number; onClose: () => void;
}) {
  const q = useQuery({
    queryKey: ["ganaderia", "detalle", celda, vista, establecimiento],
    queryFn: () => fetchDetalleGanadero(celda.grupo, celda.rubro, celda.periodo, vista, establecimiento),
  });
  return (
    <SideDrawer open onClose={onClose} title={celda.rubro} subtitulo={`${celda.periodo} · importes en pesos`} maxWidthClass="max-w-2xl">
      {q.isLoading ? <LoadingState /> : (
        <table className="w-full text-sm">
          <thead><tr className="border-b border-border text-left text-ink-secondary">
            <th className="py-1">Fecha</th><th>Comprobante</th><th>Contacto / detalle</th><th className="text-right">Importe</th>
          </tr></thead>
          <tbody>
            {(q.data?.items ?? []).map((i, n) => (
              <tr key={n} className="border-b border-border/60">
                <td className="py-1">{formatFecha(i.fecha)}</td>
                <td>{i.enlace ? <Link className="text-finance hover:underline" href={i.enlace}>{i.documento ?? "Ver"}</Link> : i.documento}</td>
                <td>{i.contacto}</td>
                <td className="text-right font-data">{formatMonto(i.importe)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <p className="mt-3 text-xs text-ink-muted">En el cuadro se muestran en {moneda === "USD" ? "dólares" : "pesos"}.</p>
    </SideDrawer>
  );
}
