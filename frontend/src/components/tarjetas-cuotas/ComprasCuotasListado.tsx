"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";

import { fetchCompras, type CompraCuotasListItem } from "@/services/tarjetasCuotasApi";
import { ContactoSelect } from "@/components/ui/ContactoSelect";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { FilterBar, FilterField, FilterSubmitButton, filterInputClass } from "@/components/ui/FilterBar";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/States";

const COLUMNS: DataTableColumn<CompraCuotasListItem>[] = [
  {
    key: "fecha",
    header: "Fecha",
    render: (c) => (
      <Link className="text-finance underline" href={`/finanzas/tarjetas/compras-en-cuotas/${c.idPagoTarjeta}`}>
        {c.fecha}
      </Link>
    ),
  },
  { key: "contacto", header: "Contacto", render: (c) => c.contacto ?? "—" },
  { key: "nroComprobante", header: "Comprobante", render: (c) => c.nroComprobante },
  { key: "cantidadCuotas", header: "Cuotas", numeric: true, render: (c) => c.cantidadCuotas },
  {
    key: "estado",
    header: "Estado",
    render: (c) => `${c.cuotasCobradas} cobradas / ${c.cuotasPendientes} pendientes`,
  },
];

interface FiltrosState {
  idContacto: string;
  contactoNombre: string;
  fechaDesde: string;
  fechaHasta: string;
}

/** Listado de compras en cuotas (Historia 3) — vacío por defecto hasta
 * aplicar un filtro (FR-006, Clarifications 2026-09-18). */
export function ComprasCuotasListado() {
  const router = useRouter();
  const searchParams = useSearchParams();

  function leerFiltrosDeUrl(): FiltrosState {
    return {
      idContacto: searchParams.get("idContacto") ?? "",
      contactoNombre: searchParams.get("contacto") ?? "",
      fechaDesde: searchParams.get("fechaDesde") ?? "",
      fechaHasta: searchParams.get("fechaHasta") ?? "",
    };
  }

  const urlFiltros = leerFiltrosDeUrl();
  const urlPage = Number(searchParams.get("page") ?? "1") || 1;
  const pageSize = 50;

  const [contacto, setContacto] = useState<{ id: number | null; nombre: string | null }>({
    id: urlFiltros.idContacto ? Number(urlFiltros.idContacto) : null,
    nombre: urlFiltros.contactoNombre || null,
  });
  const [fechaDesde, setFechaDesde] = useState(urlFiltros.fechaDesde);
  const [fechaHasta, setFechaHasta] = useState(urlFiltros.fechaHasta);

  const appliedFilters = urlFiltros;
  const page = urlPage;
  const hayFiltro = appliedFilters.idContacto !== "" || appliedFilters.fechaDesde !== "" || appliedFilters.fechaHasta !== "";

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["tarjetas-cuotas", appliedFilters, page, pageSize],
    queryFn: () =>
      fetchCompras({
        idContacto: appliedFilters.idContacto ? Number(appliedFilters.idContacto) : undefined,
        fechaDesde: appliedFilters.fechaDesde || undefined,
        fechaHasta: appliedFilters.fechaHasta || undefined,
        page,
        pageSize,
      }),
    enabled: hayFiltro,
  });

  function aplicarEnUrl(next: { filtros: FiltrosState; page: number }) {
    const params = new URLSearchParams();
    if (next.filtros.idContacto) params.set("idContacto", next.filtros.idContacto);
    if (next.filtros.contactoNombre) params.set("contacto", next.filtros.contactoNombre);
    if (next.filtros.fechaDesde) params.set("fechaDesde", next.filtros.fechaDesde);
    if (next.filtros.fechaHasta) params.set("fechaHasta", next.filtros.fechaHasta);
    if (next.page > 1) params.set("page", String(next.page));
    const qs = params.toString();
    router.replace(qs ? `/finanzas/tarjetas/compras-en-cuotas?${qs}` : "/finanzas/tarjetas/compras-en-cuotas", { scroll: false });
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    aplicarEnUrl({
      filtros: { idContacto: contacto.id ? String(contacto.id) : "", contactoNombre: contacto.nombre ?? "", fechaDesde, fechaHasta },
      page: 1,
    });
  }

  function handlePageChange(next: number) {
    aplicarEnUrl({ filtros: appliedFilters, page: next });
  }

  return (
    <div className="space-y-6">
      <FilterBar onSubmit={handleSubmit}>
        <div className="w-64">
          <ContactoSelect
            label="Contacto"
            value={contacto.id}
            razonSocial={contacto.nombre}
            onChange={(id, nombre) => setContacto({ id, nombre })}
            placeholder="Buscar contacto…"
          />
        </div>
        <FilterField label="Fecha desde">
          <input type="date" className={filterInputClass} value={fechaDesde} onChange={(e) => setFechaDesde(e.target.value)} />
        </FilterField>
        <FilterField label="Fecha hasta">
          <input type="date" className={filterInputClass} value={fechaHasta} onChange={(e) => setFechaHasta(e.target.value)} />
        </FilterField>
        <FilterSubmitButton className="ml-auto" />
      </FilterBar>

      {!hayFiltro && <EmptyState message="Aplicá al menos un filtro (contacto o fecha) para ver compras en cuotas." />}
      {hayFiltro && isLoading && <LoadingState />}
      {hayFiltro && isError && <ErrorState message="Ocurrió un error al buscar compras en cuotas." onRetry={() => refetch()} />}

      {hayFiltro && data && (
        <DataTable
          columns={COLUMNS}
          rows={data.items}
          keyField={(c) => c.idPagoTarjeta}
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
