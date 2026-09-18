"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";

import { fetchResumenes } from "@/services/tarjetasResumenesApi";
import { fetchTarjetas } from "@/services/tarjetasApi";
import { formatMoneda } from "@/lib/format";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { FilterBar, FilterField, FilterSubmitButton, filterInputClass } from "@/components/ui/FilterBar";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/States";
import type { ResumenListItem } from "@/services/tarjetasResumenesApi";

const COLUMNS: DataTableColumn<ResumenListItem>[] = [
  {
    key: "fechaCierre",
    header: "Fecha cierre",
    render: (r) => (
      <Link className="text-finance underline" href={`/finanzas/tarjetas/resumenes/${r.idResumen}`}>
        {r.fechaCierre ?? "—"}
      </Link>
    ),
  },
  { key: "tarjeta", header: "Tarjeta", render: (r) => r.tarjeta ?? "—" },
  { key: "codigo", header: "Código", render: (r) => r.codigo },
  { key: "fechaVencimiento", header: "Fecha vencimiento", render: (r) => r.fechaVencimiento ?? "—" },
  { key: "totalCalculado", header: "Total", numeric: true, render: (r) => formatMoneda(r.totalCalculado) },
  {
    key: "pagoConciliado",
    header: "Pago",
    render: (r) => (
      <span className={r.pagoConciliado ? "text-status-success" : "text-status-warning"}>
        {r.pagoConciliado ? "Conciliado" : "Pendiente"}
      </span>
    ),
  },
  {
    key: "consumosConciliados",
    header: "Consumos",
    render: (r) =>
      r.lineasTotal === 0 ? (
        <span className="text-ink-secondary">Solo cabecera</span>
      ) : (
        <span className={r.lineasVinculadas === r.lineasTotal ? "text-status-success" : "text-status-warning"}>
          {r.lineasVinculadas}/{r.lineasTotal} vinculados
        </span>
      ),
  },
  {
    key: "editar",
    header: "",
    render: (r) => (
      <Link className="text-finance underline" href={`/finanzas/tarjetas/resumenes/${r.idResumen}/editar`}>
        Editar
      </Link>
    ),
  },
];

interface FiltrosState {
  idTarjeta: string;
  fechaCierreDesde: string;
  fechaCierreHasta: string;
}

/** Listado de Resúmenes de Tarjeta (Historia 1) — vacío por defecto hasta
 * aplicar un filtro (FR-010), filtros/página persistidos en la URL. */
export function ResumenesListado() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const { data: tarjetas } = useQuery({ queryKey: ["tarjetas"], queryFn: () => fetchTarjetas(false), staleTime: Infinity });

  function leerFiltrosDeUrl(): FiltrosState {
    return {
      idTarjeta: searchParams.get("idTarjeta") ?? "",
      fechaCierreDesde: searchParams.get("fechaCierreDesde") ?? "",
      fechaCierreHasta: searchParams.get("fechaCierreHasta") ?? "",
    };
  }

  const urlFiltros = leerFiltrosDeUrl();
  const urlPage = Number(searchParams.get("page") ?? "1") || 1;
  const pageSize = 50;

  const [idTarjeta, setIdTarjeta] = useState(urlFiltros.idTarjeta);
  const [fechaCierreDesde, setFechaCierreDesde] = useState(urlFiltros.fechaCierreDesde);
  const [fechaCierreHasta, setFechaCierreHasta] = useState(urlFiltros.fechaCierreHasta);

  const appliedFilters = urlFiltros;
  const page = urlPage;
  const hayFiltro = appliedFilters.idTarjeta !== "" || appliedFilters.fechaCierreDesde !== "" || appliedFilters.fechaCierreHasta !== "";

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["tarjetas-resumenes", appliedFilters, page, pageSize],
    queryFn: () =>
      fetchResumenes({
        idTarjeta: appliedFilters.idTarjeta ? Number(appliedFilters.idTarjeta) : undefined,
        fechaCierreDesde: appliedFilters.fechaCierreDesde || undefined,
        fechaCierreHasta: appliedFilters.fechaCierreHasta || undefined,
        page,
        pageSize,
      }),
    enabled: hayFiltro,
  });

  function aplicarEnUrl(next: { filtros: FiltrosState; page: number }) {
    const params = new URLSearchParams();
    if (next.filtros.idTarjeta) params.set("idTarjeta", next.filtros.idTarjeta);
    if (next.filtros.fechaCierreDesde) params.set("fechaCierreDesde", next.filtros.fechaCierreDesde);
    if (next.filtros.fechaCierreHasta) params.set("fechaCierreHasta", next.filtros.fechaCierreHasta);
    if (next.page > 1) params.set("page", String(next.page));
    const qs = params.toString();
    router.replace(qs ? `/finanzas/tarjetas/resumenes?${qs}` : "/finanzas/tarjetas/resumenes", { scroll: false });
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    aplicarEnUrl({ filtros: { idTarjeta, fechaCierreDesde, fechaCierreHasta }, page: 1 });
  }

  function handlePageChange(next: number) {
    aplicarEnUrl({ filtros: appliedFilters, page: next });
  }

  return (
    <div className="space-y-6">
      <FilterBar onSubmit={handleSubmit}>
        <FilterField label="Tarjeta">
          <select className={filterInputClass} value={idTarjeta} onChange={(e) => setIdTarjeta(e.target.value)}>
            <option value="">Todas</option>
            {tarjetas?.map((t) => (
              <option key={t.idTarjeta} value={t.idTarjeta}>
                {t.nombre}
              </option>
            ))}
          </select>
        </FilterField>
        <FilterField label="Cierre desde">
          <input type="date" className={filterInputClass} value={fechaCierreDesde} onChange={(e) => setFechaCierreDesde(e.target.value)} />
        </FilterField>
        <FilterField label="Cierre hasta">
          <input type="date" className={filterInputClass} value={fechaCierreHasta} onChange={(e) => setFechaCierreHasta(e.target.value)} />
        </FilterField>
        <FilterSubmitButton className="ml-auto" />
      </FilterBar>

      {!hayFiltro && <EmptyState message="Aplicá al menos un filtro (tarjeta o fecha de cierre) para ver resúmenes." />}
      {hayFiltro && isLoading && <LoadingState />}
      {hayFiltro && isError && <ErrorState message="Ocurrió un error al buscar resúmenes." onRetry={() => refetch()} />}

      {hayFiltro && data && (
        <DataTable
          columns={COLUMNS}
          rows={data.items}
          keyField={(r) => r.idResumen}
          emptyMessage="Sin resultados para esta búsqueda."
          page={data.page}
          pageSize={data.pageSize}
          total={data.total}
          onPageChange={handlePageChange}
        />
      )}
    </div>
  );
}
