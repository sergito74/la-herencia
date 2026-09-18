"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

import { fetchMovimientosTarjeta } from "@/services/tarjetasApi";
import { formatMoneda } from "@/lib/format";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { ErrorState, LoadingState } from "@/components/ui/States";
import type { MovimientoTarjeta } from "@/services/tarjetasApi";

function Semaforo({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 whitespace-nowrap">
      <span
        aria-hidden
        className={`inline-block h-2.5 w-2.5 shrink-0 rounded-full ${ok ? "bg-status-success" : "bg-status-danger"}`}
      />
      <span className={ok ? "text-status-success" : "text-status-danger"}>{label}</span>
    </span>
  );
}

const COLUMNS: DataTableColumn<MovimientoTarjeta>[] = [
  {
    key: "fecha",
    header: "Fecha",
    render: (m) => (
      <Link className="text-finance underline" href={`/finanzas/tarjetas/resumenes/${m.idResumen}`}>
        {m.fecha ?? "—"}
      </Link>
    ),
  },
  { key: "codigo", header: "Resumen", render: (m) => m.codigo },
  {
    key: "origen",
    header: "Tipo",
    render: (m) => (
      <span className={m.origen === "Pago" ? "text-status-success" : "text-ink-secondary"}>
        {m.origen === "Pago" ? "Pago" : "Deuda del resumen"}
      </span>
    ),
  },
  { key: "deuda", header: "Deuda", numeric: true, render: (m) => (m.deuda ? formatMoneda(m.deuda) : "—") },
  { key: "credito", header: "Crédito", numeric: true, render: (m) => (m.credito ? formatMoneda(m.credito) : "—") },
  { key: "saldoAcumulado", header: "Saldo acumulado", numeric: true, render: (m) => formatMoneda(m.saldoAcumulado) },
  {
    key: "pagoConciliado",
    header: "Pago",
    render: (m) =>
      m.origen === "Pago" || m.pagoConciliado == null ? (
        "—"
      ) : (
        <Semaforo ok={m.pagoConciliado} label={m.pagoConciliado ? "Conciliado" : "Pendiente"} />
      ),
  },
  {
    key: "consumosConciliados",
    header: "Consumos",
    render: (m) => {
      if (m.origen === "Pago" || m.lineasTotal == null || m.lineasVinculadas == null) return "—";
      if (m.lineasTotal === 0) return <Semaforo ok label="Solo cabecera" />;
      return (
        <Semaforo ok={m.lineasVinculadas === m.lineasTotal} label={`${m.lineasVinculadas}/${m.lineasTotal} vinculados`} />
      );
    },
  },
];

/** Cuenta corriente de una tarjeta (Historia 2, FR-002/FR-003) — un
 * movimiento por resumen (nunca por cuota, research.md §3), cada fila
 * navega al resumen de origen. */
export function TarjetaCuentaCorriente({ idTarjeta }: { idTarjeta: number }) {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["tarjeta-movimientos", idTarjeta],
    queryFn: () => fetchMovimientosTarjeta(idTarjeta),
  });

  if (isLoading) return <LoadingState />;
  if (isError) return <ErrorState message="Ocurrió un error al cargar la cuenta corriente." onRetry={() => refetch()} />;

  const movimientos = data?.movimientos ?? [];
  return (
    <div className="space-y-2">
      <h2 className="text-sm font-semibold text-ink-primary">{data?.tarjeta}</h2>
      <DataTable
        columns={COLUMNS}
        rows={movimientos}
        keyField={(m) => `${m.origen}-${m.idResumen}-${m.fecha}-${m.saldoAcumulado}`}
        emptyMessage="Esta tarjeta no tiene resúmenes cargados."
        page={1}
        pageSize={movimientos.length || 1}
        total={movimientos.length}
        onPageChange={() => {}}
      />
    </div>
  );
}
