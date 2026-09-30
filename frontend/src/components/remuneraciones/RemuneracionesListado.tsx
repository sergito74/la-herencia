"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { fetchRemuneraciones, urlRecibo, type Remuneracion } from "@/services/remuneracionesApi";
import { urlDocumentoLocal } from "@/services/comprasApi";
import { ContactoLink } from "@/components/ui/ContactoLink";
import { ContactoSelect } from "@/components/ui/ContactoSelect";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { FilterBar, FilterSubmitButton } from "@/components/ui/FilterBar";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/States";
import { formatMoneda } from "@/lib/format";
import {
  BASE_DOCUMENTOS_RECIBOS,
  esReciboAusente,
  normalizarDocumentoOriginal,
} from "@/lib/documentoLocal";

/** El recibo se resuelve en dos pasos: primero `dbo.Remuneraciones.Recibo`
 * (columna real, cargada a mano en ~40% de las liquidaciones — mismo
 * patrón roto "ruta#ruta#" que `documentoOriginal` de Compras/Ventas), y
 * si está vacía o es un centinela ("SIN RECIBO"), se cae al matching por
 * nombre de archivo de `GET /api/remuneraciones/{id}/recibo` (backlog
 * post-025, punto 3) — la columna manda cuando existe: es la fuente que
 * cargó una persona a mano, más confiable que adivinar por nombre.*/
function urlDelRecibo(r: Remuneracion): string {
  if (!esReciboAusente(r.recibo)) {
    return urlDocumentoLocal(normalizarDocumentoOriginal(r.recibo as string, BASE_DOCUMENTOS_RECIBOS));
  }
  return urlRecibo(r.idSalario);
}

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
    render: (r) => (r.importe != null ? formatMoneda(r.importe) : "—"),
  },
  {
    key: "recibo",
    header: "Recibo",
    render: (r) => (
      <a
        href={urlDelRecibo(r)}
        target="_blank"
        rel="noopener noreferrer"
        className="text-finance underline"
      >
        Ver
      </a>
    ),
  },
];

/**
 * Listado de liquidaciones de remuneraciones (005 US2: FR-002). Read-only.
 * "Importe (calculado)": suma de ~15 conceptos monetarios en SQL, no un
 * campo directo — Principio IV, ver data-model.md.
 */
export function RemuneracionesListado({
  highlightKey,
  empleadoInicial,
}: {
  highlightKey?: number;
  empleadoInicial?: string | null;
}) {
  const [empleado, setEmpleado] = useState<{ id: number | null; nombre: string | null }>({
    id: null,
    nombre: empleadoInicial ?? null,
  });
  const [appliedEmpleado, setAppliedEmpleado] = useState(empleadoInicial ?? "");
  const [page, setPage] = useState(1);
  const pageSize = 50;

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["remuneraciones", appliedEmpleado, page],
    queryFn: () => fetchRemuneraciones({ empleado: appliedEmpleado, page, pageSize }),
    enabled: appliedEmpleado !== "",
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

      {appliedEmpleado === "" && (
        <EmptyState message="Elegí un empleado para ver sus liquidaciones." />
      )}
      {appliedEmpleado !== "" && isLoading && <LoadingState />}
      {appliedEmpleado !== "" && isError && (
        <ErrorState message="Ocurrió un error al buscar liquidaciones." onRetry={() => refetch()} />
      )}

      {appliedEmpleado !== "" && data && (
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
