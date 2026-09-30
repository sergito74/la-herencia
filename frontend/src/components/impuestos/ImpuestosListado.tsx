"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { fetchImpuestos, type Impuesto, type OrigenImpuesto } from "@/services/impuestosApi";
import { ContactoLink } from "@/components/ui/ContactoLink";
import { ContactoSelect } from "@/components/ui/ContactoSelect";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { FilterBar, FilterField, FilterSubmitButton, filterInputClass } from "@/components/ui/FilterBar";
import { ErrorState, LoadingState } from "@/components/ui/States";
import { formatMoneda } from "@/lib/format";

const COLUMNS: DataTableColumn<Impuesto>[] = [
  { key: "fecha", header: "Fecha", numeric: true, sortValue: (i) => i.fecha, render: (i) => i.fecha ?? "—" },
  {
    key: "tipoImpuesto",
    header: "Tipo",
    sortValue: (i) => i.tipoImpuesto,
    render: (i) => (
      <span className="inline-flex items-center gap-2">
        {i.tipoImpuesto ?? "—"}
        {i.generadaDesdePago && (
          <span
            className="rounded bg-status-warning-bg px-1.5 py-0.5 text-xs text-status-warning"
            title="Boleta reconstruida desde el pago: no hay comprobante real"
          >
            Generada desde el pago
          </span>
        )}
      </span>
    ),
  },
  { key: "periodoLiquidado", header: "Período", render: (i) => i.periodoLiquidado ?? "—" },
  {
    key: "organismo",
    header: "Organismo",
    sortValue: (i) => i.organismo,
    render: (i) => (
      <ContactoLink idContacto={i.idOrganismo} razonSocial={i.organismo} tipoContacto="Organismo" />
    ),
  },
  {
    key: "importe",
    header: "Importe",
    align: "right",
    numeric: true,
    sortValue: (i) => i.importe,
    render: (i) => (i.importe != null ? formatMoneda(i.importe) : "—"),
  },
];

/**
 * Listado de impuestos (005 US1: FR-001). Read-only: no hay affordance de
 * crear/editar/eliminar (FR-008).
 */
export function ImpuestosListado({ highlightKey }: { highlightKey?: number }) {
  const [organismo, setOrganismo] = useState<{ id: number | null; nombre: string | null }>({
    id: null,
    nombre: null,
  });
  const [appliedOrganismo, setAppliedOrganismo] = useState("");
  const [origen, setOrigen] = useState<OrigenImpuesto | "">("");
  const [appliedOrigen, setAppliedOrigen] = useState<OrigenImpuesto | "">("");
  const [page, setPage] = useState(1);
  const pageSize = 50;

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["impuestos", appliedOrganismo, appliedOrigen, page],
    queryFn: () =>
      fetchImpuestos({
        organismo: appliedOrganismo || undefined,
        origen: appliedOrigen || undefined,
        page,
        pageSize,
      }),
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setPage(1);
    setAppliedOrganismo(organismo.nombre ?? "");
    setAppliedOrigen(origen);
  }

  return (
    <div className="space-y-4">
      <FilterBar onSubmit={handleSubmit}>
        <ContactoSelect
          label="Organismo"
          tipoContacto="Organismo"
          value={organismo.id}
          razonSocial={organismo.nombre}
          onChange={(id, nombre) => setOrganismo({ id, nombre })}
          placeholder="Buscar organismo…"
        />
        <FilterField label="Origen">
          <select
            className={filterInputClass}
            value={origen}
            onChange={(e) => setOrigen(e.target.value as OrigenImpuesto | "")}
          >
            <option value="">Todas las boletas</option>
            <option value="generadas">Generadas desde el pago</option>
            <option value="sin-identificar">Tipo sin identificar</option>
          </select>
        </FilterField>
        <FilterSubmitButton />
      </FilterBar>

      {isLoading && <LoadingState />}
      {isError && (
        <ErrorState message="Ocurrió un error al buscar impuestos." onRetry={() => refetch()} />
      )}

      {data && (
        <DataTable
          columns={COLUMNS}
          rows={data.items}
          keyField={(i) => i.idImpuesto}
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
