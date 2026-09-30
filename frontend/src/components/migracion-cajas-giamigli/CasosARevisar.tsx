"use client";

import { useQuery } from "@tanstack/react-query";

import { fetchCasosARevisar, type CasoARevisar } from "@/services/migracionCajasGiamigliApi";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { ErrorState, LoadingState } from "@/components/ui/States";

const COLUMNS: DataTableColumn<CasoARevisar>[] = [
  { key: "hoja", header: "Hoja", sortValue: (c) => c.hoja, render: (c) => c.hoja },
  { key: "numeroFila", header: "Fila", align: "right", numeric: true, sortValue: (c) => c.numeroFila, render: (c) => c.numeroFila },
  { key: "motivo", header: "Motivo", sortValue: (c) => c.motivo, render: (c) => c.motivo },
  {
    key: "datosCrudos",
    header: "Datos originales",
    render: (c) => <code className="text-xs text-ink-secondary">{c.datosCrudos ?? "—"}</code>,
  },
];

/** Cola de solo lectura de filas de "Cajas Giamigli.xlsx" que no se
 * pudieron migrar automáticamente con confianza (027 US2) — nunca se
 * pierden en silencio, quedan acá con su motivo para revisión manual. */
export function CasosARevisar() {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["migracion-cajas-giamigli-revision"],
    queryFn: () => fetchCasosARevisar(false),
  });

  return (
    <div className="space-y-4">
      {isLoading && <LoadingState />}
      {isError && <ErrorState message="Ocurrió un error al obtener los casos a revisar." onRetry={() => refetch()} />}

      {data && (
        <DataTable
          columns={COLUMNS}
          rows={data.items}
          keyField={(c) => c.idRevision}
          emptyMessage="No hay casos pendientes de revisión."
          page={1}
          pageSize={Math.max(data.items.length, 1)}
          total={data.items.length}
          onPageChange={() => {}}
        />
      )}
    </div>
  );
}
