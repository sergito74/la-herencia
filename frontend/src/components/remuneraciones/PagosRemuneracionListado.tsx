"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { fetchPagosRemuneracion, type PagoRemuneracion } from "@/services/remuneracionesApi";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { ErrorState, LoadingState } from "@/components/ui/States";

const COLUMNS: DataTableColumn<PagoRemuneracion>[] = [
  { key: "fecha", header: "Fecha", numeric: true, sortValue: (p) => p.fecha, render: (p) => p.fecha ?? "—" },
  { key: "cuenta", header: "Cuenta", render: (p) => p.cuenta ?? "—" },
  { key: "caja", header: "Caja", render: (p) => p.caja ?? "—" },
  {
    key: "importe",
    header: "Importe",
    align: "right",
    numeric: true,
    sortValue: (p) => p.importe,
    render: (p) => (p.importe != null ? p.importe.toLocaleString("es-AR") : "—"),
  },
];

/**
 * Listado independiente de pagos de remuneraciones (005 US2: FR-002).
 * NO se vincula a un empleado ni a una liquidación específica: no existe
 * una clave confiable para esa relación (confirmado contra datos reales,
 * ver research.md) — el sistema MUST NOT sugerir esa relación en la UI.
 */
export function PagosRemuneracionListado() {
  const [page, setPage] = useState(1);
  const pageSize = 50;

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["remuneraciones-pagos", page],
    queryFn: () => fetchPagosRemuneracion({ page, pageSize }),
  });

  return (
    <div className="space-y-4">
      <p className="rounded-sm border border-status-warning bg-status-warning-bg px-3 py-2 text-sm text-status-warning">
        Los pagos no están vinculados a liquidaciones ni empleados individuales en el
        sistema origen.
      </p>

      {isLoading && <LoadingState />}
      {isError && <ErrorState message="Ocurrió un error al buscar pagos." onRetry={() => refetch()} />}

      {data && (
        <DataTable
          columns={COLUMNS}
          rows={data.items}
          keyField={(p) => p.idPago}
          emptyMessage="Sin pagos registrados."
          page={data.page}
          pageSize={data.pageSize}
          total={data.total}
          onPageChange={setPage}
        />
      )}
    </div>
  );
}
