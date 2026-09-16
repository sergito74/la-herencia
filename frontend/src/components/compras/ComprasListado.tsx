"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";

import { fetchCompras, fetchFiltrosCompras, type Compra } from "@/services/comprasApi";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { FilterBar, FilterField, FilterSubmitButton, filterInputClass } from "@/components/ui/FilterBar";
import { ErrorState, LoadingState } from "@/components/ui/States";

const COLUMNS: DataTableColumn<Compra>[] = [
  {
    key: "fecha",
    header: "Fecha",
    numeric: true,
    sortValue: (c) => c.fecha,
    render: (c) => (
      <Link className="text-finance underline" href={`/compras/${c.idCompra}`}>
        {c.fecha ?? "—"}
      </Link>
    ),
  },
  {
    key: "proveedor",
    header: "Proveedor",
    sortValue: (c) => c.proveedor?.razonSocial ?? null,
    render: (c) => c.proveedor?.razonSocial ?? "—",
  },
  { key: "tipoDocumento", header: "Tipo documento", render: (c) => c.tipoDocumento ?? "—" },
  { key: "numeroDocumento", header: "Nro. documento", render: (c) => c.numeroDocumento ?? "—" },
];

/**
 * Search + results table for compras (US1: FR-001, FR-002, FR-012, FR-013).
 * Filtros de Centro de Costos y Rubro replican el formulario Access real
 * `Frm Listado Compras` (ver design/agroux-frontend-redesign.md §5.1).
 * Read-only: no create/edit/delete affordance exists here (FR-010).
 */
export function ComprasListado() {
  const [proveedor, setProveedor] = useState("");
  const [numeroDocumento, setNumeroDocumento] = useState("");
  const [fechaDesde, setFechaDesde] = useState("");
  const [fechaHasta, setFechaHasta] = useState("");
  const [idCentroCosto, setIdCentroCosto] = useState("");
  const [idRubro, setIdRubro] = useState("");
  const [page, setPage] = useState(1);
  const pageSize = 50;

  const [appliedFilters, setAppliedFilters] = useState({
    proveedor: "",
    numeroDocumento: "",
    fechaDesde: "",
    fechaHasta: "",
    idCentroCosto: "",
    idRubro: "",
  });

  const { data: filtros } = useQuery({
    queryKey: ["compras-filtros"],
    queryFn: fetchFiltrosCompras,
    staleTime: Infinity,
  });

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["compras", appliedFilters, page, pageSize],
    queryFn: () =>
      fetchCompras({
        proveedor: appliedFilters.proveedor || undefined,
        numeroDocumento: appliedFilters.numeroDocumento || undefined,
        fechaDesde: appliedFilters.fechaDesde || undefined,
        fechaHasta: appliedFilters.fechaHasta || undefined,
        idCentroCosto: appliedFilters.idCentroCosto ? Number(appliedFilters.idCentroCosto) : undefined,
        idRubro: appliedFilters.idRubro ? Number(appliedFilters.idRubro) : undefined,
        page,
        pageSize,
      }),
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setPage(1);
    setAppliedFilters({ proveedor, numeroDocumento, fechaDesde, fechaHasta, idCentroCosto, idRubro });
  }

  return (
    <div className="space-y-6">
      <FilterBar onSubmit={handleSubmit}>
        <FilterField label="Proveedor">
          <input
            className={filterInputClass}
            value={proveedor}
            onChange={(e) => setProveedor(e.target.value)}
            placeholder="Razón social"
          />
        </FilterField>
        <FilterField label="Nro. documento">
          <input
            className={filterInputClass}
            value={numeroDocumento}
            onChange={(e) => setNumeroDocumento(e.target.value)}
            placeholder="0001-00012345"
          />
        </FilterField>
        <FilterField label="Fecha desde">
          <input
            type="date"
            className={filterInputClass}
            value={fechaDesde}
            onChange={(e) => setFechaDesde(e.target.value)}
          />
        </FilterField>
        <FilterField label="Fecha hasta">
          <input
            type="date"
            className={filterInputClass}
            value={fechaHasta}
            onChange={(e) => setFechaHasta(e.target.value)}
          />
        </FilterField>
        <FilterField label="Centro de costos">
          <select
            className={filterInputClass}
            value={idCentroCosto}
            onChange={(e) => setIdCentroCosto(e.target.value)}
          >
            <option value="">Todos</option>
            {filtros?.centrosCosto.map((c) => (
              <option key={c.idCentroCosto} value={c.idCentroCosto}>
                {c.centroCosto ?? `#${c.idCentroCosto}`}
              </option>
            ))}
          </select>
        </FilterField>
        <FilterField label="Rubro">
          <select className={filterInputClass} value={idRubro} onChange={(e) => setIdRubro(e.target.value)}>
            <option value="">Todos</option>
            {filtros?.rubros.map((r) => (
              <option key={r.idRubro} value={r.idRubro}>
                {r.rubro ?? `#${r.idRubro}`}
              </option>
            ))}
          </select>
        </FilterField>
        <FilterSubmitButton />
      </FilterBar>

      {isLoading && <LoadingState />}
      {isError && (
        <ErrorState message="Ocurrió un error al buscar compras." onRetry={() => refetch()} />
      )}

      {data && (
        <DataTable
          columns={COLUMNS}
          rows={data.items}
          keyField={(c) => c.idCompra}
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
