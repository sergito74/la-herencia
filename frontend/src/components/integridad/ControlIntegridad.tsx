"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { KpiCard } from "@/components/ui/KpiCard";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/States";
import { formatFecha, formatMoneda } from "@/lib/format";
import { fetchControl, type CategoriaHallazgo, type HallazgoIntegridad } from "@/services/integridadVinculosApi";

export const ETIQUETAS: Record<CategoriaHallazgo, string> = {
  "documento-excedido": "Facturas imputadas de más",
  "movimiento-excedido": "Movimientos aplicados de más",
  "doble-imputacion": "Dobles imputaciones",
  "fecha-incoherente": "Pago muy anterior a la factura",
  "moneda-mezclada": "us$ contra pesos",
};

function detalle(h: HallazgoIntegridad): string {
  switch (h.categoria) {
    case "documento-excedido":
      return Object.entries(h.imputadoPorVia)
        .map(([via, importe]) => `${via}: ${formatMoneda(importe)}`)
        .join(" · ");
    case "fecha-incoherente":
      return `Pago ${h.diasAntes} días antes de la factura`;
    case "doble-imputacion":
      return "Ya pagada vía tarjeta o cheque propio";
    case "moneda-mezclada":
      return "Importe cargado en us$ contra un movimiento en pesos";
    default:
      return "";
  }
}

const MAX_FILAS = 500;

export function ControlIntegridad() {
  const [categoria, setCategoria] = useState<CategoriaHallazgo | undefined>();
  const q = useQuery({ queryKey: ["integridad-control", categoria], queryFn: () => fetchControl(categoria) });

  if (q.isLoading) return <LoadingState />;
  if (q.isError || !q.data) return <ErrorState message="No se pudo calcular el control de integridad." onRetry={() => q.refetch()} />;

  const { totales, hallazgos } = q.data;
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-5 gap-3">
        {(Object.keys(ETIQUETAS) as CategoriaHallazgo[]).map((c) => (
          <button
            key={c}
            type="button"
            className={`text-left ${categoria === c ? "ring-2 ring-finance" : ""} rounded-md`}
            onClick={() => setCategoria(categoria === c ? undefined : c)}
          >
            <KpiCard label={ETIQUETAS[c]} value={String(totales[c])} tone={totales[c] ? "warning" : "success"} />
          </button>
        ))}
      </div>
      {hallazgos.length === 0 ? (
        <EmptyState message="Sin inconsistencias en esta categoría." />
      ) : (
        <>
          <table className="w-full text-sm">
            <thead className="bg-surface-sunken text-left text-xs text-ink-secondary">
              <tr>
                <th className="px-3 py-2">Categoría</th>
                <th className="px-3 py-2">Documento</th>
                <th className="px-3 py-2">Fecha</th>
                <th className="px-3 py-2">Movimiento</th>
                <th className="px-3 py-2 text-right">Importe</th>
                <th className="px-3 py-2 text-right">Exceso</th>
                <th className="px-3 py-2">Detalle</th>
              </tr>
            </thead>
            <tbody>
              {hallazgos.slice(0, MAX_FILAS).map((h, i) => (
                <tr key={i} className="border-t border-border">
                  <td className="px-3 py-1.5">{ETIQUETAS[h.categoria]}</td>
                  <td className="px-3 py-1.5">{h.tipoDocumento ? `${h.tipoDocumento} #${h.idDocumento}` : "—"}</td>
                  <td className="px-3 py-1.5">{formatFecha(h.fechaDocumento)}</td>
                  <td className="px-3 py-1.5">{h.origenMovimiento ? `${h.origenMovimiento} #${h.idMovimiento}` : "—"}</td>
                  <td className="font-data px-3 py-1.5 text-right">
                    {h.importe !== null ? formatMoneda(h.importe) : h.totalDocumento !== null ? formatMoneda(h.totalDocumento) : ""}
                  </td>
                  <td className="font-data px-3 py-1.5 text-right text-status-danger">
                    {h.exceso !== null ? formatMoneda(h.exceso) : ""}
                  </td>
                  <td className="px-3 py-1.5 text-xs text-ink-secondary">{detalle(h)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {hallazgos.length > MAX_FILAS && (
            <p className="text-xs text-ink-secondary">
              Se muestran {MAX_FILAS} de {hallazgos.length}. Elegí una categoría para acotar.
            </p>
          )}
        </>
      )}
    </div>
  );
}
