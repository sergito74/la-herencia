"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";

import { fetchCompras, fetchFiltrosCompras, TIPOS_CONTACTO_COMPRA, type Compra } from "@/services/comprasApi";
import { ContactoLink } from "@/components/ui/ContactoLink";
import { ContactoSelect } from "@/components/ui/ContactoSelect";
import { DataTable, type DataTableColumn, type SortState } from "@/components/ui/DataTable";
import { FilterBar, FilterField, FilterSubmitButton, filterInputClass } from "@/components/ui/FilterBar";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/States";

const COLUMNS: DataTableColumn<Compra>[] = [
  {
    key: "fecha",
    header: "Fecha",
    numeric: true,
    sortValue: (c) => c.fecha,
    render: (c) => (
      // Clic en la fecha abre el mismo formulario de carga/edición (no el
      // PDF original) — pedido explícito del usuario (2026-09-17).
      <Link
        className="text-finance underline"
        href={`/compras/${c.idCompra}/editar`}
        title="Ver/editar esta compra."
      >
        {c.fecha ?? "—"}
      </Link>
    ),
  },
  {
    key: "proveedor",
    header: "Proveedor",
    sortValue: (c) => c.proveedor?.razonSocial ?? null,
    render: (c) => (
      <ContactoLink
        idContacto={c.proveedor?.idContacto}
        razonSocial={c.proveedor?.razonSocial}
        tipoContacto="Proveedor"
      />
    ),
  },
  {
    key: "tipoDocumento",
    header: "Tipo documento",
    sortValue: (c) => c.tipoDocumento,
    render: (c) => c.tipoDocumento ?? "—",
  },
  {
    key: "numeroDocumento",
    header: "Nro. documento",
    sortValue: (c) => c.numeroDocumento,
    render: (c) => c.numeroDocumento ?? "—",
  },
  {
    key: "editar",
    header: "",
    render: (c) => (
      <Link className="text-finance underline" href={`/compras/${c.idCompra}/editar`}>
        Editar
      </Link>
    ),
  },
];

interface FiltrosState {
  proveedorNombre: string;
  numeroDocumento: string;
  fechaDesde: string;
  fechaHasta: string;
  idCentroCosto: string;
  idRubro: string;
  productoServicio: string;
  idDestino: string;
  campania: string;
}

const CAMPOS_FILTRO: (keyof FiltrosState)[] = [
  "proveedorNombre",
  "numeroDocumento",
  "fechaDesde",
  "fechaHasta",
  "idCentroCosto",
  "idRubro",
  "productoServicio",
  "idDestino",
  "campania",
];

/**
 * Search + results table for compras (US1: FR-001, FR-002, FR-012, FR-013).
 * Filtros de Centro de Costos y Rubro replican el formulario Access real
 * `Frm Listado Compras` (ver design/agroux-frontend-redesign.md §5.1).
 * Desde 006-carga-compras agrega el acceso a alta (`/compras/nueva`).
 *
 * Filtros/orden/página viven en la URL (no en `useState` local) — así
 * "Volver a Compras" desde la pantalla de edición (botón que hace
 * `router.back()`) recupera exactamente la misma búsqueda, en vez de
 * perderla al desmontarse el componente (pedido explícito del usuario,
 * 2026-09-17, tras comprobar que la versión con estado local no persistía).
 */
export function ComprasListado() {
  const router = useRouter();
  const searchParams = useSearchParams();

  function leerFiltrosDeUrl(): FiltrosState {
    return {
      proveedorNombre: searchParams.get("proveedorNombre") ?? "",
      numeroDocumento: searchParams.get("numeroDocumento") ?? "",
      fechaDesde: searchParams.get("fechaDesde") ?? "",
      fechaHasta: searchParams.get("fechaHasta") ?? "",
      idCentroCosto: searchParams.get("idCentroCosto") ?? "",
      idRubro: searchParams.get("idRubro") ?? "",
      productoServicio: searchParams.get("productoServicio") ?? "",
      idDestino: searchParams.get("idDestino") ?? "",
      campania: searchParams.get("campania") ?? "",
    };
  }

  const urlFiltros = leerFiltrosDeUrl();
  const urlProveedorId = searchParams.get("proveedorId");
  const urlPage = Number(searchParams.get("page") ?? "1") || 1;
  const urlSortKey = searchParams.get("sortKey");
  const urlSortDir = searchParams.get("sortDir");
  const urlSort: SortState =
    urlSortKey && (urlSortDir === "asc" || urlSortDir === "desc")
      ? { key: urlSortKey, direction: urlSortDir }
      : null;

  // Campos del formulario (borrador, hasta que se aplica con "Buscar") —
  // se inicializan desde la URL para que al volver se vea lo mismo que se
  // había tipeado, no solo lo que ya se había aplicado.
  const [proveedor, setProveedor] = useState<{ id: number | null; nombre: string | null }>({
    id: urlProveedorId ? Number(urlProveedorId) : null,
    nombre: urlFiltros.proveedorNombre || null,
  });
  const [numeroDocumento, setNumeroDocumento] = useState(urlFiltros.numeroDocumento);
  const [fechaDesde, setFechaDesde] = useState(urlFiltros.fechaDesde);
  const [fechaHasta, setFechaHasta] = useState(urlFiltros.fechaHasta);
  const [idCentroCosto, setIdCentroCosto] = useState(urlFiltros.idCentroCosto);
  const [idRubro, setIdRubro] = useState(urlFiltros.idRubro);
  const [productoServicio, setProductoServicio] = useState(urlFiltros.productoServicio);
  const [idDestino, setIdDestino] = useState(urlFiltros.idDestino);
  const [campania, setCampania] = useState(urlFiltros.campania);
  const pageSize = 50;

  // Lo efectivamente aplicado (lo que se buscó) — fuente de verdad: la URL.
  const appliedFilters = urlFiltros;
  const page = urlPage;
  const sort = urlSort;

  const { data: filtros } = useQuery({
    queryKey: ["compras-filtros"],
    queryFn: fetchFiltrosCompras,
    staleTime: Infinity,
  });

  // Sin filtro no se pide/muestra nada — mismo criterio que Contactos
  // (pedido explícito del usuario, 2026-09-17): con miles de compras
  // acumuladas, un listado por defecto solo confunde (parece que "faltan"
  // registros que en realidad están más adelante, sin filtrar).
  const hayFiltro = CAMPOS_FILTRO.some((campo) => appliedFilters[campo] !== "");

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["compras", appliedFilters, page, pageSize, sort],
    queryFn: () =>
      fetchCompras({
        proveedor: appliedFilters.proveedorNombre || undefined,
        numeroDocumento: appliedFilters.numeroDocumento || undefined,
        fechaDesde: appliedFilters.fechaDesde || undefined,
        fechaHasta: appliedFilters.fechaHasta || undefined,
        idCentroCosto: appliedFilters.idCentroCosto ? Number(appliedFilters.idCentroCosto) : undefined,
        idRubro: appliedFilters.idRubro ? Number(appliedFilters.idRubro) : undefined,
        productoServicio: appliedFilters.productoServicio || undefined,
        idDestino: appliedFilters.idDestino ? Number(appliedFilters.idDestino) : undefined,
        campania: appliedFilters.campania || undefined,
        sortBy: sort?.key,
        sortDir: sort?.direction,
        page,
        pageSize,
      }),
    enabled: hayFiltro,
  });

  /** Arma la URL a partir de un estado completo y la aplica con `replace`
   * (no `push`): así un cambio de página/orden no ensucia el historial —
   * "Volver" siempre cae en esta misma entrada, con lo último aplicado. */
  function aplicarEnUrl(next: {
    filtros: FiltrosState;
    proveedorId: number | null;
    page: number;
    sort: SortState;
  }) {
    const params = new URLSearchParams();
    for (const campo of CAMPOS_FILTRO) {
      if (next.filtros[campo]) params.set(campo, next.filtros[campo]);
    }
    if (next.proveedorId != null) params.set("proveedorId", String(next.proveedorId));
    if (next.page > 1) params.set("page", String(next.page));
    if (next.sort) {
      params.set("sortKey", next.sort.key);
      params.set("sortDir", next.sort.direction);
    }
    const qs = params.toString();
    router.replace(qs ? `/compras?${qs}` : "/compras", { scroll: false });
  }

  function handleSortChange(next: SortState) {
    aplicarEnUrl({
      filtros: appliedFilters,
      proveedorId: urlProveedorId ? Number(urlProveedorId) : null,
      page: 1,
      sort: next,
    });
  }

  function handlePageChange(next: number) {
    aplicarEnUrl({ filtros: appliedFilters, proveedorId: urlProveedorId ? Number(urlProveedorId) : null, page: next, sort });
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    aplicarEnUrl({
      filtros: {
        proveedorNombre: proveedor.nombre ?? "",
        numeroDocumento,
        fechaDesde,
        fechaHasta,
        idCentroCosto,
        idRubro,
        productoServicio,
        idDestino,
        campania,
      },
      proveedorId: proveedor.id,
      page: 1,
      sort,
    });
  }

  return (
    <div className="space-y-6">
      <FilterBar onSubmit={handleSubmit}>
        <div className="flex w-full items-end gap-3">
          <div className="w-64">
            <ContactoSelect
              label="Proveedor"
              tipoContacto={TIPOS_CONTACTO_COMPRA}
              value={proveedor.id}
              razonSocial={proveedor.nombre}
              onChange={(id, nombre) => setProveedor({ id, nombre })}
              placeholder="Buscar proveedor…"
            />
          </div>
          <FilterSubmitButton className="ml-auto" />
        </div>
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
        <FilterField label="Producto/Servicio">
          <input
            className={filterInputClass}
            value={productoServicio}
            onChange={(e) => setProductoServicio(e.target.value)}
            placeholder="Descripción…"
          />
        </FilterField>
        <FilterField label="Destino">
          <select className={filterInputClass} value={idDestino} onChange={(e) => setIdDestino(e.target.value)}>
            <option value="">Todos</option>
            {filtros?.destinos.map((d) => (
              <option key={d.idDestino} value={d.idDestino}>
                {d.destino ?? `#${d.idDestino}`}
              </option>
            ))}
          </select>
        </FilterField>
        <FilterField label="Campaña">
          <select className={filterInputClass} value={campania} onChange={(e) => setCampania(e.target.value)}>
            <option value="">Todas</option>
            {filtros?.campañas.map((c) => (
              <option key={c.idCampania} value={c.campania ?? ""}>
                {c.campania ?? `#${c.idCampania}`}
              </option>
            ))}
          </select>
        </FilterField>
      </FilterBar>

      {!hayFiltro && (
        <EmptyState message="Aplicá al menos un filtro (proveedor, documento, fecha, etc.) para ver compras." />
      )}
      {hayFiltro && isLoading && <LoadingState />}
      {hayFiltro && isError && (
        <ErrorState message="Ocurrió un error al buscar compras." onRetry={() => refetch()} />
      )}

      {hayFiltro && data && (
        <DataTable
          columns={COLUMNS}
          rows={data.items}
          keyField={(c) => c.idCompra}
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
