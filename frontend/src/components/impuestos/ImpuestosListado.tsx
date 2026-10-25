"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";

import { SoloLectura } from "@/components/auth/SoloLectura";

import { fetchImpuestos, type Impuesto } from "@/services/impuestosApi";
import { ContactoLink } from "@/components/ui/ContactoLink";
import { ContactoSelect } from "@/components/ui/ContactoSelect";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { FilterBar, FilterSubmitButton } from "@/components/ui/FilterBar";
import { ErrorState, LoadingState } from "@/components/ui/States";
import { formatMoneda, formatFecha } from "@/lib/format";

const COLUMNS: DataTableColumn<Impuesto>[] = [
  {
    key: "fecha",
    header: "Fecha",
    numeric: true,
    sortValue: (i) => i.fecha,
    render: (i) => (
      <Link href={`/finanzas/impuestos/${i.idImpuesto}/editar`} className="text-finance underline" title="Ver o editar la boleta">
        {formatFecha(i.fecha)}
      </Link>
    ),
  },
  { key: "tipoImpuesto", header: "Tipo", sortValue: (i) => i.tipoImpuesto, render: (i) => i.tipoImpuesto ?? "—" },
  { key: "periodoLiquidado", header: "Período", render: (i) => i.periodoLiquidado ?? "—" },
  { key: "numeroDocumento", header: "Nº documento", render: (i) => i.numeroDocumento ?? "—" },
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
  {
    key: "aCargoDe",
    header: "A cargo de socio",
    render: (i) =>
      i.aCargoDe?.length ? (
        <span title={i.pendienteNominal ? `Pendiente $${i.pendienteNominal}` : undefined}>
          {i.aCargoDe.map((a) => a.socio).join(", ")}
          {i.estadoDevolucion && (
            <span className={`ml-1 rounded px-1 text-xs ${i.estadoDevolucion === "devuelto" ? "bg-green-100" : "bg-amber-100"}`}>
              {i.estadoDevolucion === "devuelto" ? "devuelto" : i.estadoDevolucion === "parcial" ? "devuelto parcial" : "pendiente"}
            </span>
          )}
        </span>
      ) : "",
  },
];

/**
 * Listado de impuestos (005 US1: FR-001). Desde 033-alta-impuestos: botón
 * "Nueva boleta"; la fecha abre la boleta para editarla o eliminarla.
 */
export function ImpuestosListado({ highlightKey }: { highlightKey?: number }) {
  const [organismo, setOrganismo] = useState<{ id: number | null; nombre: string | null }>({
    id: null,
    nombre: null,
  });
  const [appliedOrganismo, setAppliedOrganismo] = useState("");
  const [particular, setParticular] = useState(false);
  const [page, setPage] = useState(1);
  const pageSize = 50;

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["impuestos", appliedOrganismo, particular, page],
    queryFn: () =>
      fetchImpuestos({ organismo: appliedOrganismo || undefined, page, pageSize, particular }),
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setPage(1);
    setAppliedOrganismo(organismo.nombre ?? "");
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
        <label className="flex items-center gap-1 self-end text-sm">
          <input type="checkbox" checked={particular} onChange={(e) => { setParticular(e.target.checked); setPage(1); }} />
          A cargo de socio
        </label>
        <FilterSubmitButton />
        <SoloLectura>
          <Link
            href="/finanzas/impuestos/nueva"
            className="ml-auto self-end rounded bg-finance px-3 py-1.5 text-sm text-white"
          >
            Nueva boleta
          </Link>
        </SoloLectura>
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
