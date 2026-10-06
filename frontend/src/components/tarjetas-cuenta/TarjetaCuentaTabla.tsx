"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";

import { ErrorState, LoadingState } from "@/components/ui/States";
import { formatFecha, formatMoneda } from "@/lib/format";
import {
  fetchCuentaTarjeta,
  urlExportarCuentaTarjeta,
  type AgruparCuenta,
  type EstadoVinculo,
  type FilaCuenta,
} from "@/services/tarjetasCuentaApi";

const VINCULO: Record<EstadoVinculo, string> = {
  vinculado: "Con proveedor",
  "resto-con-proveedor": "Resto del proveedor",
  "sin-proveedor": "Sin proveedor",
  "cruzado-con-devolucion": "Cruzado con devolución",
};

function destino(f: FilaCuenta): string | null {
  const r = f.referencia;
  if (!r) return null;
  if (r.tipo === "movimiento-bancario" && r.medio && r.idMovimiento) {
    return `/finanzas/tesoreria?medio=${r.medio}&highlight=${r.idMovimiento}`;
  }
  if (r.tipo === "cruce") return "/finanzas/tarjetas/control";
  if (r.idResumen) return `/finanzas/tarjetas/resumenes/${r.idResumen}`;
  return null;
}

/** Cuenta de una tarjeta: movimientos cronológicos o por resumen, con filtros y exportación (034, FR-010/FR-011). */
export function TarjetaCuentaTabla({ idTarjeta }: { idTarjeta: number }) {
  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");
  const [agrupar, setAgrupar] = useState<AgruparCuenta>("movimientos");
  const filtros = { desde: desde || undefined, hasta: hasta || undefined, agrupar };
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["tarjeta-cuenta", idTarjeta, desde, hasta, agrupar],
    queryFn: () => fetchCuentaTarjeta(idTarjeta, filtros),
    refetchOnMount: "always",
  });

  if (isLoading) return <LoadingState />;
  if (isError || !data) return <ErrorState message="Ocurrió un error al cargar la cuenta de la tarjeta." onRetry={() => refetch()} />;

  return (
    <div className="space-y-2">
      <h2 className="text-sm font-semibold text-ink-primary">{data.tarjeta}</h2>
      <div className="flex flex-wrap items-end gap-3 text-xs">
        <label className="flex flex-col">
          Desde
          <input type="date" value={desde} onChange={(e) => setDesde(e.target.value)} className="rounded border border-line px-2 py-1" />
        </label>
        <label className="flex flex-col">
          Hasta
          <input type="date" value={hasta} onChange={(e) => setHasta(e.target.value)} className="rounded border border-line px-2 py-1" />
        </label>
        <label className="flex items-center gap-1">
          <input
            type="checkbox"
            checked={agrupar === "resumenes"}
            onChange={(e) => setAgrupar(e.target.checked ? "resumenes" : "movimientos")}
          />
          Ver por resumen
        </label>
        <a className="text-finance underline" href={urlExportarCuentaTarjeta(idTarjeta, filtros)}>
          Exportar a Excel
        </a>
      </div>

      {data.apertura.contactoAnterior && (
        <p className="rounded border border-line px-3 py-2 text-xs text-ink-secondary">
          Administración anterior ({data.apertura.contactoAnterior}): los pagos de esa etapa figuran aparte como apertura informativa y no forman
          parte de este saldo.
        </p>
      )}

      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs text-ink-secondary">
            <th className="py-1">Fecha</th>
            <th>Tipo</th>
            <th>Resumen</th>
            <th>Detalle</th>
            <th>Proveedor</th>
            <th className="text-right">Deuda</th>
            <th className="text-right">Crédito</th>
            <th className="text-right">Saldo</th>
            <th>Vínculo</th>
          </tr>
        </thead>
        <tbody>
          <tr className="border-t border-line text-ink-secondary">
            <td colSpan={7} className="py-1">Saldo inicial</td>
            <td className="text-right">{formatMoneda(data.saldoInicial)}</td>
            <td />
          </tr>
          {data.filas.map((f, i) => {
            const href = destino(f);
            return (
              <tr key={`${f.origen}-${i}`} className="border-t border-line">
                <td className="py-1">{formatFecha(f.fecha)}</td>
                <td>{f.origen}</td>
                <td>
                  {href ? (
                    <Link className="text-finance underline" href={href}>
                      {f.codigo ?? f.idResumen}
                    </Link>
                  ) : (
                    f.codigo
                  )}
                </td>
                <td>{href && !f.codigo ? <Link className="text-finance underline" href={href}>{f.detalle}</Link> : f.detalle}</td>
                <td>{f.proveedor}</td>
                <td className="text-right">{f.deuda ? formatMoneda(f.deuda) : "—"}</td>
                <td className="text-right">{f.credito ? formatMoneda(f.credito) : "—"}</td>
                <td className="text-right">{formatMoneda(f.saldo)}</td>
                <td className="text-xs">{f.estadoVinculo ? VINCULO[f.estadoVinculo] : ""}</td>
              </tr>
            );
          })}
          {data.filas.length === 0 && (
            <tr>
              <td colSpan={9} className="py-3 text-center text-ink-secondary">No hay movimientos en el período.</td>
            </tr>
          )}
        </tbody>
        <tfoot>
          <tr className="border-t border-line font-semibold">
            <td colSpan={7} className="py-1">Saldo final</td>
            <td className="text-right">{formatMoneda(data.saldoFinal)}</td>
            <td />
          </tr>
          <tr className="text-xs text-ink-secondary">
            <td colSpan={7}>De eso, exigible (resúmenes ya cerrados)</td>
            <td className="text-right">{formatMoneda(data.detalleSaldo.exigible)}</td>
            <td />
          </tr>
          <tr className="text-xs text-ink-secondary">
            <td colSpan={7}>De eso, consumos todavía sin resumen</td>
            <td className="text-right">{formatMoneda(data.detalleSaldo.noResumido)}</td>
            <td />
          </tr>
        </tfoot>
      </table>

      {data.cuotasAVencer.length > 0 && (
        <section>
          <h3 className="text-xs font-semibold">Cuotas a vencer (informativo)</h3>
          <ul className="text-xs">
            {data.cuotasAVencer.map((c, i) => (
              <li key={i}>
                {formatFecha(c.fechaVencimiento)} — {formatMoneda(c.importe)}
              </li>
            ))}
          </ul>
        </section>
      )}
      <p className="text-xs text-ink-secondary">{data.avisoSaldo}</p>
    </div>
  );
}
