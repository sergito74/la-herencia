"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import {
  fetchRetencionesVentaHacienda,
  type RetencionVentaHacienda,
} from "@/services/ventasHaciendaApi";
import { ContactoLink } from "@/components/ui/ContactoLink";
import { ContactoSelect } from "@/components/ui/ContactoSelect";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { FilterBar, FilterSubmitButton } from "@/components/ui/FilterBar";
import { ErrorState, LoadingState } from "@/components/ui/States";

const COLUMNS: DataTableColumn<RetencionVentaHacienda>[] = [
  { key: "fecha", header: "Fecha", numeric: true, sortValue: (r) => r.fecha, render: (r) => r.fecha ?? "—" },
  {
    key: "contacto",
    header: "Contacto",
    sortValue: (r) => r.contacto,
    render: (r) => <ContactoLink idContacto={r.idContacto} razonSocial={r.contacto} />,
  },
  {
    key: "documento",
    header: "Documento",
    render: (r) => `${r.documento ?? "—"} ${r.numeroDocumento ?? ""}`.trim(),
  },
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
 * Listado independiente de retenciones de venta de hacienda (005 US4:
 * FR-004). NO se anida bajo una venta: no existe una clave confiable
 * hacia una venta específica (confirmado contra datos reales, ver
 * research.md).
 */
export function RetencionesVentaHaciendaListado({ highlightKey }: { highlightKey?: number }) {
  const [contacto, setContacto] = useState<{ id: number | null; nombre: string | null }>({
    id: null,
    nombre: null,
  });
  const [appliedContacto, setAppliedContacto] = useState("");
  const [page, setPage] = useState(1);
  const pageSize = 50;

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["ventas-hacienda-retenciones", appliedContacto, page],
    queryFn: () =>
      fetchRetencionesVentaHacienda({
        contacto: appliedContacto || undefined,
        page,
        pageSize,
      }),
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setPage(1);
    setAppliedContacto(contacto.nombre ?? "");
  }

  return (
    <div className="space-y-4">
      <p className="rounded-sm border border-status-warning bg-status-warning-bg px-3 py-2 text-sm text-status-warning">
        Listado independiente — no existe una relación confiable en los datos de origen
        hacia una venta específica.
      </p>

      <FilterBar onSubmit={handleSubmit}>
        <ContactoSelect
          label="Contacto"
          value={contacto.id}
          razonSocial={contacto.nombre}
          onChange={(id, nombre) => setContacto({ id, nombre })}
          placeholder="Buscar contacto…"
        />
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
          highlightKey={highlightKey}
        />
      )}
    </div>
  );
}
