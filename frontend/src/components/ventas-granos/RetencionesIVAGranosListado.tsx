"use client";

import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { cargarRetencionIVAGranos, fetchRetencionesIVAGranos, type RetencionIVAGranos } from "@/services/ventasGranosApi";
import { MoneyInput } from "@/components/ui/MoneyInput";
import { SoloLectura } from "@/components/auth/SoloLectura";
import { urlDocumentoLocal } from "@/services/comprasApi";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { ErrorState, LoadingState } from "@/components/ui/States";
import { formatFecha, formatMoneda } from "@/lib/format";

const ESTADO: Record<RetencionIVAGranos["estado"], { texto: string; clase: string }> = {
  devuelto: { texto: "Devuelto", clase: "bg-status-success-bg text-status-success" },
  pendiente: { texto: "Pendiente", clase: "bg-status-warning-bg text-status-warning" },
  vencido: { texto: "Vencido", clase: "bg-status-danger-bg text-status-danger" },
  aplicado: { texto: "Sin devolución (crédito aplicado)", clase: "bg-status-neutral-bg text-ink-secondary" },
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
        ) : r.estado === "aplicado" ? null : (
          <span className="text-xs text-ink-secondary">hace {r.dias} días</span>
        )}
      </span>
    ),
  },
];

/** Alta a mano de un certificado que el lector no pudo leer (24/11/2026). */
function CargarCertificado({ cerrar }: { cerrar: () => void }) {
  const qc = useQueryClient();
  const [coe, setCoe] = useState("");
  const [certificado, setCertificado] = useState("");
  const [importe, setImporte] = useState(0);
  const [archivo, setArchivo] = useState("");
  const alta = useMutation({
    mutationFn: () => cargarRetencionIVAGranos({ coe, certificado, importe, archivo: archivo || null }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["ventas-granos-retenciones-iva"] }); cerrar(); },
  });
  const campo = "rounded-md border border-border px-2 py-1 text-sm";
  return (
    <form className="flex flex-wrap items-end gap-3 rounded-md border border-border bg-surface-sunken p-3"
      onSubmit={(e) => { e.preventDefault(); alta.mutate(); }}>
      <label className="flex flex-col text-xs text-ink-secondary">COE de la liquidación
        <input className={campo} value={coe} onChange={(e) => setCoe(e.target.value)} placeholder="330132967323" required />
      </label>
      <label className="flex flex-col text-xs text-ink-secondary">N.º de certificado
        <input className={campo} value={certificado} onChange={(e) => setCertificado(e.target.value)} placeholder="09601-2026-212205" required />
      </label>
      <label className="flex flex-col text-xs text-ink-secondary">Importe retenido
        <MoneyInput className={`${campo} w-36 text-right`} value={importe} moneda="Pesos" onChange={setImporte} />
      </label>
      <label className="flex min-w-[20rem] flex-1 flex-col text-xs text-ink-secondary">PDF del certificado (ruta, opcional)
        <input className={campo} value={archivo} onChange={(e) => setArchivo(e.target.value)} placeholder="C:\Users\...\Retenciones ...\archivo.pdf" />
      </label>
      <button type="submit" disabled={alta.isPending} className="rounded-md bg-finance px-3 py-1 text-sm text-white disabled:opacity-50">Guardar</button>
      <button type="button" onClick={cerrar} className="rounded-md border border-border px-3 py-1 text-sm">Cancelar</button>
      {alta.isError && <p className="w-full text-sm text-status-danger">{alta.error.message}</p>}
    </form>
  );
}

/** 24/11/2026: certificados RETIVA de ventas de granos (la retención va aparte de la venta) y su devolución por ARCA,
 * asociada sola desde los extractos (transferencias «AFIP 5000 625»). Vencido = más de 90 días sin devolución. */
export function RetencionesIVAGranosListado() {
  const [soloAbiertas, setSoloAbiertas] = useState(false);
  const [cargando, setCargando] = useState(false);
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
        {data.resumen.aplicado > 0 && <span>Aplicado a otros impuestos: <strong>{formatMoneda(data.resumen.aplicado)}</strong></span>}
        <span className={data.resumen.cantidadVencidos ? "text-status-danger" : ""}>
          Vencido (más de 90 días): <strong>{formatMoneda(data.resumen.vencido)}</strong>
          {data.resumen.cantidadVencidos > 0 && ` (${data.resumen.cantidadVencidos})`}
        </span>
        <SoloLectura>
          <button type="button" onClick={() => setCargando(true)} className="rounded-md bg-finance px-3 py-1 text-sm text-white">
            Cargar certificado
          </button>
        </SoloLectura>
        <label className="ml-auto flex items-center gap-1 text-xs">
          <input type="checkbox" checked={soloAbiertas} onChange={(e) => { setSoloAbiertas(e.target.checked); setPage(1); }} />
          Solo sin devolver
        </label>
      </div>
      {cargando && <CargarCertificado cerrar={() => setCargando(false)} />}
      <DataTable columns={COLUMNS} rows={filas.slice((page - 1) * pageSize, page * pageSize)} keyField={(r) => r.idRetencion}
        emptyMessage="Sin retenciones." page={page} pageSize={pageSize} total={filas.length} onPageChange={setPage} />
    </div>
  );
}
