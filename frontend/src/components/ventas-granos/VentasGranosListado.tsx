"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";

import { fetchVentasGranos, TIPOS_CONTACTO_VENTA_GRANOS, type VentaGranos } from "@/services/ventasGranosApi";
import { ContactoLink } from "@/components/ui/ContactoLink";
import { ContactoSelect } from "@/components/ui/ContactoSelect";
import { DataTable, type DataTableColumn, type SortState } from "@/components/ui/DataTable";
import { FilterBar, FilterField, FilterSubmitButton, filterInputClass } from "@/components/ui/FilterBar";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/States";

const COLUMNS: DataTableColumn<VentaGranos>[] = [
  {
    key: "fecha",
    header: "Fecha",
    numeric: true,
    sortValue: (v) => v.fecha,
    render: (v) => (
      <Link className="text-finance underline" href={`/ventas/granos/${v.idVenta}/editar`}>
        {v.fecha ?? "—"}
      </Link>
    ),
  },
  {
    key: "consignatario",
    header: "Consignatario",
    sortValue: (v) => v.consignatario?.razonSocial ?? null,
    render: (v) => (
      <ContactoLink
        idContacto={v.consignatario?.idContacto}
        razonSocial={v.consignatario?.razonSocial}
        tipoContacto="Multiple"
      />
    ),
  },
  {
    key: "tipoDocumento",
    header: "Tipo documento",
    sortValue: (v) => v.tipoDocumento,
    render: (v) => v.tipoDocumento ?? "—",
  },
  {
    key: "numeroDocumento",
    header: "Nro. documento",
    sortValue: (v) => v.numeroDocumento,
    render: (v) => v.numeroDocumento ?? "—",
  },
  { key: "grano", header: "Grano", sortValue: (v) => v.grano, render: (v) => v.grano ?? "—" },
  { key: "campania", header: "Campaña", sortValue: (v) => v.campania, render: (v) => v.campania ?? "—" },
  {
    key: "editar",
    header: "",
    render: (v) => (
      <Link className="text-finance underline" href={`/ventas/granos/${v.idVenta}/editar`}>
        Editar
      </Link>
    ),
  },
];

interface FiltrosState {
  consignatario: string;
  numeroDocumento: string;
  fechaDesde: string;
  fechaHasta: string;
  campania: string;
}

const CAMPOS_FILTRO: (keyof FiltrosState)[] = [
  "consignatario",
  "numeroDocumento",
  "fechaDesde",
  "fechaHasta",
  "campania",
];

/**
 * Listado de Ventas de Granos (007, US5): vacío por defecto hasta aplicar
 * un filtro (FR-010, mismo criterio que Compras/Contactos), con filtros/
 * orden/página persistidos en la URL (mismo patrón que `ComprasListado.tsx`).
 */
export function VentasGranosListado() {
  const router = useRouter();
  const searchParams = useSearchParams();

  function leerFiltrosDeUrl(): FiltrosState {
    return {
      consignatario: searchParams.get("consignatario") ?? "",
      numeroDocumento: searchParams.get("numeroDocumento") ?? "",
      fechaDesde: searchParams.get("fechaDesde") ?? "",
      fechaHasta: searchParams.get("fechaHasta") ?? "",
      campania: searchParams.get("campania") ?? "",
    };
  }

  const urlFiltros = leerFiltrosDeUrl();
  const urlPage = Number(searchParams.get("page") ?? "1") || 1;
  const urlSortKey = searchParams.get("sortKey");
  const urlSortDir = searchParams.get("sortDir");
  const urlSort: SortState =
    urlSortKey && (urlSortDir === "asc" || urlSortDir === "desc")
      ? { key: urlSortKey, direction: urlSortDir }
      : null;

  const urlConsignatarioId = searchParams.get("consignatarioId");
  const [consignatario, setConsignatario] = useState<{ id: number | null; nombre: string | null }>({
    id: urlConsignatarioId ? Number(urlConsignatarioId) : null,
    nombre: urlFiltros.consignatario || null,
  });
  const [numeroDocumento, setNumeroDocumento] = useState(urlFiltros.numeroDocumento);
  const [fechaDesde, setFechaDesde] = useState(urlFiltros.fechaDesde);
  const [fechaHasta, setFechaHasta] = useState(urlFiltros.fechaHasta);
  const [campania, setCampania] = useState(urlFiltros.campania);
  const pageSize = 50;

  const appliedFilters = urlFiltros;
  const page = urlPage;
  const sort = urlSort;

  const hayFiltro = CAMPOS_FILTRO.some((campo) => appliedFilters[campo] !== "");

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["ventas-granos", appliedFilters, page, pageSize, sort],
    queryFn: () =>
      fetchVentasGranos({
        consignatario: appliedFilters.consignatario || undefined,
        numeroDocumento: appliedFilters.numeroDocumento || undefined,
        fechaDesde: appliedFilters.fechaDesde || undefined,
        fechaHasta: appliedFilters.fechaHasta || undefined,
        campania: appliedFilters.campania || undefined,
        sortBy: sort?.key,
        sortDir: sort?.direction,
        page,
        pageSize,
      }),
    enabled: hayFiltro,
  });

  function aplicarEnUrl(next: {
    filtros: FiltrosState;
    consignatarioId: number | null;
    page: number;
    sort: SortState;
  }) {
    const params = new URLSearchParams();
    for (const campo of CAMPOS_FILTRO) {
      if (next.filtros[campo]) params.set(campo, next.filtros[campo]);
    }
    if (next.consignatarioId != null) params.set("consignatarioId", String(next.consignatarioId));
    if (next.page > 1) params.set("page", String(next.page));
    if (next.sort) {
      params.set("sortKey", next.sort.key);
      params.set("sortDir", next.sort.direction);
    }
    const qs = params.toString();
    router.replace(qs ? `/ventas/granos?${qs}` : "/ventas/granos", { scroll: false });
  }

  function handleSortChange(next: SortState) {
    aplicarEnUrl({
      filtros: appliedFilters,
      consignatarioId: urlConsignatarioId ? Number(urlConsignatarioId) : null,
      page: 1,
      sort: next,
    });
  }

  function handlePageChange(next: number) {
    aplicarEnUrl({
      filtros: appliedFilters,
      consignatarioId: urlConsignatarioId ? Number(urlConsignatarioId) : null,
      page: next,
      sort,
    });
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    aplicarEnUrl({
      filtros: {
        consignatario: consignatario.nombre ?? "",
        numeroDocumento,
        fechaDesde,
        fechaHasta,
        campania,
      },
      consignatarioId: consignatario.id,
      page: 1,
      sort,
    });
  }

  return (
    <div className="space-y-6">
      <FilterBar onSubmit={handleSubmit}>
        <div className="w-64">
          <ContactoSelect
            label="Consignatario"
            tipoContacto={TIPOS_CONTACTO_VENTA_GRANOS}
            value={consignatario.id}
            razonSocial={consignatario.nombre}
            onChange={(id, nombre) => setConsignatario({ id, nombre })}
            placeholder="Buscar consignatario…"
          />
        </div>
        <FilterField label="Nro. documento">
          <input
            className={filterInputClass}
            value={numeroDocumento}
            onChange={(e) => setNumeroDocumento(e.target.value)}
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
        <FilterField label="Campaña">
          <input
            className={filterInputClass}
            value={campania}
            onChange={(e) => setCampania(e.target.value)}
            placeholder="Ej. 2010/2011"
          />
        </FilterField>
        <FilterSubmitButton className="ml-auto" />
      </FilterBar>

      {!hayFiltro && (
        <EmptyState message="Aplicá al menos un filtro (consignatario, documento, fecha, campaña) para ver ventas de granos." />
      )}
      {hayFiltro && isLoading && <LoadingState />}
      {hayFiltro && isError && (
        <ErrorState message="Ocurrió un error al buscar ventas de granos." onRetry={() => refetch()} />
      )}

      {hayFiltro && data && (
        <DataTable
          columns={COLUMNS}
          rows={data.items}
          keyField={(v) => v.idVenta}
          emptyMessage="Sin resultados para esta búsqueda."
          page={data.page}
          pageSize={data.pageSize}
          total={data.total}
          onPageChange={handlePageChange}
          sort={sort}
          onSortChange={handleSortChange}
        />
      )}
    </div>
  );
}
