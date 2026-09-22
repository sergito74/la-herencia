"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";

import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { ErrorState, LoadingState } from "@/components/ui/States";
import { BadgeEstadoOrden } from "@/components/ordenes/EstadosOrden";
import { fetchOrdenes, type FiltrosOrdenes, type OrdenListItem } from "@/services/ordenesApi";

const ESTADOS = [
  { value: "", label: "Todos" },
  { value: "Planificada", label: "Planificadas" },
  { value: "Ejecutada", label: "Ejecutadas" },
  { value: "Anulada", label: "Anuladas" },
];

const VACIO: FiltrosOrdenes = { fechaDesde: "", fechaHasta: "", estado: "" };

const COLUMNAS: DataTableColumn<OrdenListItem>[] = [
  {
    key: "fechaPedido",
    header: "Fecha",
    numeric: true,
    render: (o) => (
      <Link className="whitespace-nowrap text-finance underline" href={`/produccion/ordenes/${o.idOrden}`}>
        {o.fechaPedido ?? "—"}
      </Link>
    ),
  },
  { key: "tipoLabor", header: "Labor", render: (o) => o.tipoLabor ?? "—" },
  { key: "contratista", header: "Contratista", render: (o) => o.contratista ?? "Maquinaria propia" },
  { key: "estado", header: "Estado", render: (o) => <BadgeEstadoOrden estado={o.estado} /> },
];

export function OrdenesListado() {
  const [filtros, setFiltros] = useState<FiltrosOrdenes>(VACIO);
  const [page, setPage] = useState(1);
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["ordenes", filtros, page],
    queryFn: () => fetchOrdenes(filtros, page),
  });

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-3">
        <label className="text-sm">
          Desde
          <input
            type="date"
            className="mt-1 block rounded border border-border px-2 py-1.5"
            value={filtros.fechaDesde}
            onChange={(e) => setFiltros({ ...filtros, fechaDesde: e.target.value })}
          />
        </label>
        <label className="text-sm">
          Hasta
          <input
            type="date"
            className="mt-1 block rounded border border-border px-2 py-1.5"
            value={filtros.fechaHasta}
            onChange={(e) => setFiltros({ ...filtros, fechaHasta: e.target.value })}
          />
        </label>
        <label className="text-sm">
          Estado
          <select
            className="mt-1 block rounded border border-border px-2 py-1.5"
            value={filtros.estado}
            onChange={(e) => setFiltros({ ...filtros, estado: e.target.value })}
          >
            {ESTADOS.map((e) => (
              <option key={e.value} value={e.value}>
                {e.label}
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          onClick={() => {
            setPage(1);
            refetch();
          }}
          className="rounded bg-finance px-3 py-1.5 text-sm text-white"
        >
          Filtrar
        </button>
        <Link href="/produccion/ordenes/nuevo" className="ml-auto rounded bg-finance px-4 py-2 text-sm text-white">
          + Nueva orden
        </Link>
      </div>

      {isLoading && <LoadingState />}
      {isError && <ErrorState message="No se pudieron cargar las órdenes." />}
      {data && (
        <DataTable
          columns={COLUMNAS}
          rows={data.items}
          keyField={(o) => o.idOrden}
          emptyMessage="No hay órdenes de trabajo con estos filtros."
          page={data.page}
          pageSize={data.pageSize}
          total={data.total}
          onPageChange={setPage}
        />
      )}
    </div>
  );
}
