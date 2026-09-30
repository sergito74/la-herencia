"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import {
  fetchMovimientosCaja,
  fetchSaldoCaja,
  type CajaSlug,
  type MovimientoCajaEfectivo,
} from "@/services/cajasEfectivoApi";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { KpiCard } from "@/components/ui/KpiCard";
import { ErrorState, LoadingState } from "@/components/ui/States";
import { formatFecha, formatMoneda } from "@/lib/format";

const NOMBRES: Record<CajaSlug, string> = {
  "giamigli-sa": "Caja de efectivo — Giamigli SA",
  "campo-chica": "Caja chica del campo",
};

const COLUMNS: DataTableColumn<MovimientoCajaEfectivo>[] = [
  { key: "fecha", header: "Fecha", sortValue: (m) => m.fecha, render: (m) => formatFecha(m.fecha) },
  { key: "concepto", header: "Concepto", sortValue: (m) => m.concepto ?? "", render: (m) => m.concepto ?? "—" },
  { key: "detalle", header: "Detalle", sortValue: (m) => m.detalle ?? "", render: (m) => m.detalle ?? "—" },
  {
    key: "importe",
    header: "Importe",
    align: "right",
    numeric: true,
    sortValue: (m) => m.importe,
    render: (m) => (
      <span className={m.importe < 0 ? "text-status-danger" : "text-status-success"}>{formatMoneda(m.importe)}</span>
    ),
  },
  { key: "cuenta", header: "Cuenta", render: (m) => m.cuenta ?? "—" },
  { key: "formaPago", header: "Forma de pago", render: (m) => m.formaPago ?? "—" },
];

/** Cuenta de una caja de efectivo (027 US3/US4): saldo + historial, 100%
 * de solo lectura — no hay affordance de carga (FR-011). */
export function CajaEfectivo({ caja }: { caja: CajaSlug }) {
  const [page, setPage] = useState(1);
  const pageSize = 50;

  const { data: saldo, isLoading: cargandoSaldo } = useQuery({
    queryKey: ["caja-efectivo-saldo", caja],
    queryFn: () => fetchSaldoCaja(caja),
  });

  const {
    data: movimientos,
    isLoading,
    isError,
    refetch,
  } = useQuery({
    queryKey: ["caja-efectivo-movimientos", caja, page, pageSize],
    queryFn: () => fetchMovimientosCaja(caja, { page, pageSize }),
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4 rounded-md border border-border bg-surface p-4">
        <h2 className="text-lg font-semibold text-ink-primary">{NOMBRES[caja]}</h2>
        <KpiCard
          label="Saldo"
          value={cargandoSaldo ? "…" : formatMoneda(saldo?.saldo ?? 0)}
          tone={saldo && saldo.saldo < 0 ? "danger" : "success"}
        />
      </div>

      {isLoading && <LoadingState />}
      {isError && <ErrorState message="Ocurrió un error al obtener los movimientos." onRetry={() => refetch()} />}

      {movimientos && (
        <DataTable
          columns={COLUMNS}
          rows={movimientos.items}
          keyField={(m) => m.idMovimiento}
          emptyMessage="Sin movimientos registrados para esta caja."
          page={movimientos.page}
          pageSize={movimientos.pageSize}
          total={movimientos.total}
          onPageChange={setPage}
        />
      )}
    </div>
  );
}
