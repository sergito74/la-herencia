"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { fetchVentasHacienda } from "@/services/ventasHaciendaApi";

/**
 * Listado de ventas de hacienda: consignatario a nivel de venta, comprador
 * por línea de detalle (Nota UX de plan.md). Read-only (005 US4: FR-004).
 */
export function VentasHaciendaListado() {
  const [consignatario, setConsignatario] = useState("");
  const [appliedConsignatario, setAppliedConsignatario] = useState("");
  const [page, setPage] = useState(1);
  const pageSize = 50;

  const { data, isLoading, isError } = useQuery({
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

  const totalPages = data ? Math.max(1, Math.ceil(data.total / data.pageSize)) : 1;

  return (
    <div className="space-y-4">
      <form onSubmit={handleSubmit} className="flex gap-2 rounded-lg border border-slate-200 bg-white p-4">
        <label className="flex flex-1 flex-col gap-1 text-sm">
          Consignatario
          <input
            className="rounded border border-slate-300 px-2 py-1"
            value={consignatario}
            onChange={(e) => setConsignatario(e.target.value)}
            placeholder="Razón social"
          />
        </label>
        <button
          type="submit"
          className="self-end rounded bg-slate-900 px-4 py-2 text-sm text-white hover:bg-slate-700"
        >
          Buscar
        </button>
      </form>

      {isLoading && <p className="text-slate-600">Cargando…</p>}
      {isError && <p className="text-red-700">Ocurrió un error al buscar ventas.</p>}

      {data && data.items.length === 0 && (
        <p className="rounded border border-slate-200 bg-white p-6 text-center text-slate-600">
          Sin resultados para esta búsqueda.
        </p>
      )}

      {data && data.items.length > 0 && (
        <>
          <div className="space-y-4">
            {data.items.map((v) => (
              <div key={v.idVenta} className="rounded-lg border border-slate-200 bg-white p-4">
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <div>
                    <h3 className="font-semibold text-slate-900">
                      Venta {v.numeroDocumento ?? "—"}
                    </h3>
                    <p className="text-sm text-slate-600">
                      {v.fecha ?? "—"} · Consignatario: {v.consignatario ?? "—"}
                    </p>
                  </div>
                </div>

                <table className="mt-3 min-w-full divide-y divide-slate-200 text-sm">
                  <thead className="text-left text-slate-500">
                    <tr>
                      <th className="px-2 py-1">Comprador</th>
                      <th className="px-2 py-1">Tipo de hacienda</th>
                      <th className="px-2 py-1 text-right">Cantidad</th>
                      <th className="px-2 py-1 text-right">Precio unit. (A)</th>
                      <th className="px-2 py-1 text-right">Precio unit. (B)</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {v.lineas.map((l) => (
                      <tr key={l.idDetalleVenta}>
                        <td className="px-2 py-1">{l.comprador ?? "—"}</td>
                        <td className="px-2 py-1">{l.tipoHacienda ?? "—"}</td>
                        <td className="px-2 py-1 text-right">
                          {l.cantidad ?? "—"} {l.unidadMedida ?? ""}
                        </td>
                        <td className="px-2 py-1 text-right">
                          {l.precioUnitarioA != null
                            ? l.precioUnitarioA.toLocaleString("es-AR")
                            : "—"}
                        </td>
                        <td className="px-2 py-1 text-right">
                          {l.precioUnitarioB != null
                            ? l.precioUnitarioB.toLocaleString("es-AR")
                            : "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ))}
          </div>

          <div className="flex items-center justify-between text-sm text-slate-600">
            <span>
              Página {data.page} de {totalPages} — {data.total} ventas
            </span>
            <div className="flex gap-2">
              <button
                className="rounded border border-slate-300 px-3 py-1 disabled:opacity-40"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                Anterior
              </button>
              <button
                className="rounded border border-slate-300 px-3 py-1 disabled:opacity-40"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
              >
                Siguiente
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
