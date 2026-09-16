"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { fetchVentasHacienda, type VentaHacienda } from "@/services/ventasHaciendaApi";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { FilterBar, FilterField, FilterSubmitButton, filterInputClass } from "@/components/ui/FilterBar";
import { SideDrawer } from "@/components/ui/SideDrawer";
import { ErrorState, LoadingState } from "@/components/ui/States";

const COLUMNS: DataTableColumn<VentaHacienda>[] = [
  { key: "fecha", header: "Fecha", numeric: true, sortValue: (v) => v.fecha, render: (v) => v.fecha ?? "—" },
  { key: "numeroDocumento", header: "Documento", render: (v) => v.numeroDocumento ?? "—" },
  {
    key: "consignatario",
    header: "Consignatario",
    sortValue: (v) => v.consignatario,
    render: (v) => v.consignatario ?? "—",
  },
  { key: "lineas", header: "Líneas", numeric: true, render: (v) => v.lineas.length },
];

/**
 * Listado de ventas de hacienda: consignatario a nivel de venta, comprador
 * por línea de detalle (Nota UX de plan.md). El detalle por comprador se
 * ve en un `SideDrawer` para no incrustar tablas gigantes en el listado
 * (design/agroux-frontend-redesign.md §4.3/§5.4). Read-only (005 US4: FR-004).
 */
export function VentasHaciendaListado() {
  const [consignatario, setConsignatario] = useState("");
  const [appliedConsignatario, setAppliedConsignatario] = useState("");
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<VentaHacienda | null>(null);
  const pageSize = 50;

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["ventas-hacienda", appliedConsignatario, page],
    queryFn: () =>
      fetchVentasHacienda({
        consignatario: appliedConsignatario || undefined,
        page,
        pageSize,
      }),
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setPage(1);
    setAppliedConsignatario(consignatario);
  }

  const columns: DataTableColumn<VentaHacienda>[] = COLUMNS.map((col) =>
    col.key === "numeroDocumento"
      ? {
          ...col,
          render: (v) => (
            <button className="text-finance underline" onClick={() => setSelected(v)}>
              {v.numeroDocumento ?? "—"}
            </button>
          ),
        }
      : col
  );

  return (
    <div className="space-y-4">
      <FilterBar onSubmit={handleSubmit}>
        <FilterField label="Consignatario">
          <input
            className={filterInputClass}
            value={consignatario}
            onChange={(e) => setConsignatario(e.target.value)}
            placeholder="Razón social"
          />
        </FilterField>
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
          onPageChange={setPage}
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
              {selected.fecha ?? "—"} · Consignatario: {selected.consignatario ?? "—"}
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
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {selected.lineas.map((l) => (
                  <tr key={l.idDetalleVenta}>
                    <td className="py-1">{l.comprador ?? "—"}</td>
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
