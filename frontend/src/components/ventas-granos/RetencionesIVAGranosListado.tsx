"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { fetchRetencionesIVAGranos, type RetencionIVAGranos } from "@/services/ventasGranosApi";
import { urlDocumentoLocal } from "@/services/comprasApi";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { ErrorState, LoadingState } from "@/components/ui/States";
import { formatFecha, formatMoneda } from "@/lib/format";

const ESTADO: Record<RetencionIVAGranos["estado"], { texto: string; clase: string }> = {
  devuelto: { texto: "Devuelto", clase: "bg-status-success-bg text-status-success" },
  pendiente: { texto: "Pendiente", clase: "bg-status-warning-bg text-status-warning" },
  vencido: { texto: "Vencido", clase: "bg-status-danger-bg text-status-danger" },
};

const COLUMNS: DataTableColumn<RetencionIVAGranos>[] = [
  { key: "fecha", header: "Fecha", numeric: true, sortValue: (r) => r.fecha ?? "", render: (r) => formatFecha(r.fecha) },
  { key: "agente", header: "Agente", sortValue: (r) => r.agente ?? "", render: (r) => r.agente ?? "—" },
  {
    key: "certificado", header: "Certificado", sortValue: (r) => r.certificado,
    render: (r) => (r.archivo ? <a className="text-finance hover:underline" href={urlDocumentoLocal(r.archivo)} target="_blank" rel="noreferrer">{r.certificado}</a> : r.certificado),
  },
  {
    key: "coe", header: "Liquidación", sortValue: (r) => r.coe ?? "",
    render: (r) => <Link className="text-finance hover:underline" href={`/ventas/granos/${r.idVenta}/editar`}>{r.coe ?? r.idVenta}</Link>,
  },
  { key: "grano", header: "Grano", sortValue: (r) => r.grano ?? "", render: (r) => `${r.grano ?? "—"} ${r.campania ?? ""}`.trim() },
  { key: "importe", header: "Retenido", numeric: true, sortValue: (r) => r.importe, render: (r) => formatMoneda(r.importe) },
  {
    key: "estado", header: "Devolución", sortValue: (r) => r.estado,
    render: (r) => (
      <span className="flex flex-wrap items-center gap-2">
        <span className={`rounded-sm px-1.5 text-xs ${ESTADO[r.estado].clase}`}>{ESTADO[r.estado].texto}</span>
        {r.devolucion ? (
          <span className="text-xs text-ink-secondary">
            {formatFecha(r.devolucion.fecha)} · {r.devolucion.banco}
            {r.devolucion.agrupa > 1 && ` · junto con ${r.devolucion.agrupa - 1} más (${formatMoneda(r.devolucion.importe)})`}
            {!r.devolucion.exacto && " · con otras retenciones sin certificado"}
          </span>
        ) : (
          <span className="text-xs text-ink-secondary">hace {r.dias} días</span>
        )}
      </span>
    ),
  },
];

/** 24/11/2026: certificados RETIVA de ventas de granos (la retención va aparte de la venta) y su devolución por ARCA,
 * asociada sola desde los extractos (transferencias «AFIP 5000 625»). Vencido = más de 90 días sin devolución. */
export function RetencionesIVAGranosListado() {
  const [soloAbiertas, setSoloAbiertas] = useState(false);
  const [page, setPage] = useState(1);
  const pageSize = 50;
  const q = useQuery({ queryKey: ["ventas-granos-retenciones-iva"], queryFn: fetchRetencionesIVAGranos });
  if (q.isLoading) return <LoadingState />;
  if (q.isError) return <ErrorState message="No se pudieron leer las retenciones de IVA de granos." onRetry={() => q.refetch()} />;
  const data = q.data!;
  const filas = soloAbiertas ? data.items.filter((r) => r.estado !== "devuelto") : data.items;
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-4 text-sm">
        <span>Devuelto: <strong>{formatMoneda(data.resumen.devuelto)}</strong></span>
        <span>Pendiente: <strong>{formatMoneda(data.resumen.pendiente)}</strong></span>
        <span className={data.resumen.cantidadVencidos ? "text-status-danger" : ""}>
          Vencido (más de 90 días): <strong>{formatMoneda(data.resumen.vencido)}</strong>
          {data.resumen.cantidadVencidos > 0 && ` (${data.resumen.cantidadVencidos})`}
        </span>
        <label className="ml-auto flex items-center gap-1 text-xs">
          <input type="checkbox" checked={soloAbiertas} onChange={(e) => { setSoloAbiertas(e.target.checked); setPage(1); }} />
          Solo sin devolver
        </label>
      </div>
      <DataTable columns={COLUMNS} rows={filas.slice((page - 1) * pageSize, page * pageSize)} keyField={(r) => r.idRetencion}
        emptyMessage="Sin retenciones." page={page} pageSize={pageSize} total={filas.length} onPageChange={setPage} />
    </div>
  );
}
