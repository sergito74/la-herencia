"use client";

import { useQuery } from "@tanstack/react-query";

import { fetchHistorial, type Reasignacion } from "@/services/reasignacionContactoApi";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { ErrorState, LoadingState } from "@/components/ui/States";

const COLUMNS: DataTableColumn<Reasignacion>[] = [
  { key: "fecha", header: "Fecha", render: (r) => r.fecha?.slice(0, 16).replace("T", " ") ?? "—" },
  { key: "origen", header: "Origen", render: (r) => `${r.origen} #${r.idOrigen}` },
  {
    key: "cambio",
    header: "Cambio",
    render: (r) => (
      <span>
        {r.contactoAnterior ?? r.idContactoAnterior} → <strong>{r.contactoNuevo ?? r.idContactoNuevo}</strong>
      </span>
    ),
  },
  { key: "motivo", header: "Motivo", render: (r) => r.motivo ?? "—" },
  { key: "usuario", header: "Usuario", render: (r) => r.usuario },
];

/** Historial general de reasignaciones aplicadas (022, US3) — auditoría
 * sin necesidad de acceso técnico directo a la base (FR-005). */
export function HistorialReasignaciones() {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["reasignacion-historial"],
    queryFn: () => fetchHistorial(),
  });

  return (
    <div className="space-y-4">
      {isLoading && <LoadingState />}
      {isError && <ErrorState message="Ocurrió un error al obtener el historial." onRetry={() => refetch()} />}

      {data && (
        <DataTable
          columns={COLUMNS}
          rows={data.items}
          keyField={(r) => r.idReasignacion}
          emptyMessage="Todavía no se aplicó ninguna reasignación."
          page={1}
          pageSize={Math.max(data.items.length, 1)}
          total={data.items.length}
          onPageChange={() => {}}
        />
      )}
    </div>
  );
}
