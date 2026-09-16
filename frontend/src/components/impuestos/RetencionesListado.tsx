"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { fetchRetenciones, type Retencion } from "@/services/impuestosApi";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { FilterBar, FilterField, FilterSubmitButton, filterInputClass } from "@/components/ui/FilterBar";
import { ErrorState, LoadingState } from "@/components/ui/States";

const COLUMNS: DataTableColumn<Retencion>[] = [
  { key: "fecha", header: "Fecha", numeric: true, sortValue: (r) => r.fecha, render: (r) => r.fecha ?? "—" },
  { key: "numeroCertificado", header: "Certificado", render: (r) => r.numeroCertificado ?? "—" },
  { key: "contacto", header: "Contacto", sortValue: (r) => r.contacto, render: (r) => r.contacto ?? "—" },
  {
    key: "importe",
    header: "Importe",
    align: "right",
    numeric: true,
    sortValue: (r) => r.importe,
    render: (r) => (r.importe != null ? r.importe.toLocaleString("es-AR") : "—"),
  },
];

/**
 * Listado de retenciones impositivas (005 US1: FR-001). Read-only.
 */
export function RetencionesListado() {
  const [contacto, setContacto] = useState("");
  const [appliedContacto, setAppliedContacto] = useState("");
  const [page, setPage] = useState(1);
  const pageSize = 50;

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["impuestos-retenciones", appliedContacto, page],
    queryFn: () =>
      fetchRetenciones({ contacto: appliedContacto || undefined, page, pageSize }),
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setPage(1);
    setAppliedContacto(contacto);
  }

  return (
    <div className="space-y-4">
      <FilterBar onSubmit={handleSubmit}>
        <FilterField label="Contacto">
          <input
            className={filterInputClass}
            value={contacto}
            onChange={(e) => setContacto(e.target.value)}
            placeholder="Razón social"
          />
        </FilterField>
        <FilterSubmitButton />
      </FilterBar>

      {isLoading && <LoadingState />}
      {isError && (
        <ErrorState message="Ocurrió un error al buscar retenciones." onRetry={() => refetch()} />
      )}

      {data && (
        <DataTable
          columns={COLUMNS}
          rows={data.items}
          keyField={(r) => r.idRetencion}
          emptyMessage="Sin resultados para esta búsqueda."
          page={data.page}
          pageSize={data.pageSize}
          total={data.total}
          onPageChange={setPage}
        />
      )}
    </div>
  );
}
