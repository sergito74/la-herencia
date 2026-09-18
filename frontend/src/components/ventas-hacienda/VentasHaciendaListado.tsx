"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";

import { fetchVentasHacienda, TIPOS_CONTACTO_VENTA_HACIENDA, type VentaHacienda } from "@/services/ventasHaciendaApi";
import { ContactoLink } from "@/components/ui/ContactoLink";
import { ContactoSelect } from "@/components/ui/ContactoSelect";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { FilterBar, FilterSubmitButton } from "@/components/ui/FilterBar";
import { SideDrawer } from "@/components/ui/SideDrawer";
import { ErrorState, LoadingState } from "@/components/ui/States";

/**
 * Listado de ventas de hacienda: consignatario a nivel de venta, comprador
 * por línea de detalle (Nota UX de plan.md). El detalle por comprador se
 * ve en un `SideDrawer` para no incrustar tablas gigantes en el listado
 * (design/agroux-frontend-redesign.md §4.3/§5.4). Desde 007 agrega el
 * enlace a edición y persiste filtro/página en la URL (mismo patrón que
 * `ComprasListado.tsx`, T032a) — así "← Volver a Ventas de Hacienda"
 * recupera la búsqueda anterior en vez de perderla.
 */
export function VentasHaciendaListado() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const urlConsignatario = searchParams.get("consignatario") ?? "";
  const urlPage = Number(searchParams.get("page") ?? "1") || 1;

  const urlConsignatarioId = searchParams.get("consignatarioId");
  const [consignatario, setConsignatario] = useState<{ id: number | null; nombre: string | null }>({
    id: urlConsignatarioId ? Number(urlConsignatarioId) : null,
    nombre: urlConsignatario || null,
  });
  const [selected, setSelected] = useState<VentaHacienda | null>(null);
  const pageSize = 50;

  const appliedConsignatario = urlConsignatario;
  const page = urlPage;

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["ventas-hacienda", appliedConsignatario, page],
    queryFn: () =>
      fetchVentasHacienda({
        consignatario: appliedConsignatario || undefined,
        page,
        pageSize,
      }),
  });

  function aplicarEnUrl(next: { consignatario: string; consignatarioId: number | null; page: number }) {
    const params = new URLSearchParams();
    if (next.consignatario) params.set("consignatario", next.consignatario);
    if (next.consignatarioId != null) params.set("consignatarioId", String(next.consignatarioId));
    if (next.page > 1) params.set("page", String(next.page));
    const qs = params.toString();
    router.replace(qs ? `/ventas/hacienda?${qs}` : "/ventas/hacienda", { scroll: false });
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    aplicarEnUrl({ consignatario: consignatario.nombre ?? "", consignatarioId: consignatario.id, page: 1 });
  }

  function handlePageChange(next: number) {
    aplicarEnUrl({
      consignatario: appliedConsignatario,
      consignatarioId: urlConsignatarioId ? Number(urlConsignatarioId) : null,
      page: next,
    });
  }

  const columns: DataTableColumn<VentaHacienda>[] = [
    {
      key: "fecha",
      header: "Fecha",
      numeric: true,
      sortValue: (v) => v.fecha,
      render: (v) => (
        <Link className="text-finance underline" href={`/ventas/hacienda/${v.idVenta}/editar`}>
          {v.fecha ?? "—"}
        </Link>
      ),
    },
    {
      key: "numeroDocumento",
      header: "Documento",
      render: (v) => (
        <button className="text-finance underline" onClick={() => setSelected(v)}>
          {v.numeroDocumento ?? "—"}
        </button>
      ),
    },
    {
      key: "consignatario",
      header: "Consignatario",
      sortValue: (v) => v.consignatario,
      render: (v) => (
        <ContactoLink idContacto={v.idConsignatario} razonSocial={v.consignatario} tipoContacto="Consignatario" />
      ),
    },
    {
      key: "editar",
      header: "",
      render: (v) => (
        <Link className="text-finance underline" href={`/ventas/hacienda/${v.idVenta}/editar`}>
          Editar
        </Link>
      ),
    },
  ];

  return (
    <div className="space-y-4">
      <FilterBar onSubmit={handleSubmit}>
        <div className="w-64">
          <ContactoSelect
            label="Consignatario"
            tipoContacto={TIPOS_CONTACTO_VENTA_HACIENDA}
            value={consignatario.id}
            razonSocial={consignatario.nombre}
            onChange={(id, nombre) => setConsignatario({ id, nombre })}
            placeholder="Buscar consignatario…"
          />
        </div>
        <FilterSubmitButton />
      </FilterBar>

      {isLoading && <LoadingState />}
      {isError && <ErrorState message="Ocurrió un error al buscar ventas." onRetry={() => refetch()} />}

      {data && (
        <DataTable
          columns={columns}
          rows={data.items}
          keyField={(v) => v.idVenta}
          emptyMessage="Sin resultados para esta búsqueda."
          page={data.page}
          pageSize={data.pageSize}
          total={data.total}
          onPageChange={handlePageChange}
        />
      )}

      <SideDrawer
        open={selected !== null}
        onClose={() => setSelected(null)}
        title={`Venta ${selected?.numeroDocumento ?? "—"}`}
      >
        {selected && (
          <div className="space-y-3">
            <p className="text-sm text-ink-secondary">
              {selected.fecha ?? "—"} · Consignatario:{" "}
              <ContactoLink
                idContacto={selected.idConsignatario}
                razonSocial={selected.consignatario}
                tipoContacto="Consignatario"
              />
            </p>
            <table className="min-w-full divide-y divide-border text-sm">
              <thead className="text-left text-ink-secondary">
                <tr>
                  <th className="py-1">Comprador</th>
                  <th className="py-1">Tipo</th>
                  <th className="py-1 text-right">Cant.</th>
                  <th className="py-1 text-right" title="Datos de origen, unidades no siempre consistentes">
                    Precio (A)
                  </th>
                  <th className="py-1 text-right" title="Datos de origen, unidades no siempre consistentes">
                    Precio (B)
                  </th>
                  <th className="py-1 text-right">Importe</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {selected.lineas.map((l) => (
                  <tr key={l.idDetalleVenta}>
                    <td className="py-1">
                      <ContactoLink idContacto={l.idComprador} razonSocial={l.comprador} tipoContacto="Comprador" />
                    </td>
                    <td className="py-1">{l.tipoHacienda ?? "—"}</td>
                    <td className="py-1 text-right font-data">
                      {l.cantidad ?? "—"} {l.unidadMedida ?? ""}
                    </td>
                    <td className="py-1 text-right font-data">
                      {l.precioUnitarioA != null ? l.precioUnitarioA.toLocaleString("es-AR") : "—"}
                    </td>
                    <td className="py-1 text-right font-data">
                      {l.precioUnitarioB != null ? l.precioUnitarioB.toLocaleString("es-AR") : "—"}
                    </td>
                    <td className="py-1 text-right font-data font-medium">
                      {l.importe != null ? l.importe.toLocaleString("es-AR") : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </SideDrawer>
    </div>
  );
}
