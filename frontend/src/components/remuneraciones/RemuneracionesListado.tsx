"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { fetchRemuneraciones, type Remuneracion } from "@/services/remuneracionesApi";
import { ContactoLink } from "@/components/ui/ContactoLink";
import { ContactoSelect } from "@/components/ui/ContactoSelect";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { FilterBar, FilterSubmitButton } from "@/components/ui/FilterBar";
import { ErrorState, LoadingState } from "@/components/ui/States";

const COLUMNS: DataTableColumn<Remuneracion>[] = [
  {
    key: "fechaPago",
    header: "Fecha de pago",
    numeric: true,
    sortValue: (r) => r.fechaPago,
    render: (r) => r.fechaPago ?? "—",
  },
  { key: "periodoLiquidado", header: "Período", render: (r) => r.periodoLiquidado ?? "—" },
  {
    key: "empleado",
    header: "Empleado",
    sortValue: (r) => r.empleado,
    render: (r) =>
      r.idContacto != null ? (
        <ContactoLink idContacto={r.idContacto} razonSocial={r.empleado} tipoContacto="Empleado" />
      ) : (
        <span className="italic text-ink-muted">Contacto no disponible</span>
      ),
  },
  {
    key: "importe",
    header: "Importe liquidado (calculado)",
    align: "right",
    numeric: true,
    sortValue: (r) => r.importe,
    render: (r) => (r.importe != null ? r.importe.toLocaleString("es-AR") : "—"),
  },
];

/**
 * Listado de liquidaciones de remuneraciones (005 US2: FR-002). Read-only.
 * "Importe (calculado)": suma de ~15 conceptos monetarios en SQL, no un
 * campo directo — Principio IV, ver data-model.md.
 */
export function RemuneracionesListado({ highlightKey }: { highlightKey?: number }) {
  const [empleado, setEmpleado] = useState<{ id: number | null; nombre: string | null }>({
    id: null,
    nombre: null,
  });
  const [appliedEmpleado, setAppliedEmpleado] = useState("");
  const [page, setPage] = useState(1);
  const pageSize = 50;

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["remuneraciones", appliedEmpleado, page],
    queryFn: () =>
      fetchRemuneraciones({ empleado: appliedEmpleado || undefined, page, pageSize }),
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setPage(1);
    setAppliedEmpleado(empleado.nombre ?? "");
  }

  return (
    <div className="space-y-4">
      <FilterBar onSubmit={handleSubmit}>
        <ContactoSelect
          label="Empleado"
          tipoContacto="Empleado"
          value={empleado.id}
          razonSocial={empleado.nombre}
          onChange={(id, nombre) => setEmpleado({ id, nombre })}
          placeholder="Buscar empleado…"
        />
        <FilterSubmitButton />
      </FilterBar>

      {isLoading && <LoadingState />}
      {isError && (
        <ErrorState message="Ocurrió un error al buscar liquidaciones." onRetry={() => refetch()} />
      )}

      {data && (
        <DataTable
          columns={COLUMNS}
          rows={data.items}
          keyField={(r) => r.idSalario}
          emptyMessage="Sin resultados para esta búsqueda."
          page={data.page}
          pageSize={data.pageSize}
          total={data.total}
          onPageChange={setPage}
          highlightKey={highlightKey}
        />
      )}
    </div>
  );
}
