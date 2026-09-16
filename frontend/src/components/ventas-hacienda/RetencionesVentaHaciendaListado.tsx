"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { fetchRetencionesVentaHacienda } from "@/services/ventasHaciendaApi";

/**
 * Listado independiente de retenciones de venta de hacienda (005 US4:
 * FR-004). NO se anida bajo una venta: no existe una clave confiable
 * hacia una venta específica (confirmado contra datos reales, ver
 * research.md).
 */
export function RetencionesVentaHaciendaListado() {
  const [contacto, setContacto] = useState("");
  const [appliedContacto, setAppliedContacto] = useState("");
  const [page, setPage] = useState(1);
  const pageSize = 50;

  const { data, isLoading, isError } = useQuery({
    queryKey: ["ventas-hacienda-retenciones", appliedContacto, page],
    queryFn: () =>
      fetchRetencionesVentaHacienda({
        contacto: appliedContacto || undefined,
        page,
        pageSize,
      }),
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setPage(1);
    setAppliedContacto(contacto);
  }

  const totalPages = data ? Math.max(1, Math.ceil(data.total / data.pageSize)) : 1;

  return (
    <div className="space-y-4">
      <p className="text-sm text-slate-600">
        Retenciones sobre ventas de hacienda. Listado independiente — no existe una
        relación confiable en los datos de origen hacia una venta específica.
      </p>

      <form onSubmit={handleSubmit} className="flex gap-2 rounded-lg border border-slate-200 bg-white p-4">
        <label className="flex flex-1 flex-col gap-1 text-sm">
          Contacto
          <input
            className="rounded border border-slate-300 px-2 py-1"
            value={contacto}
            onChange={(e) => setContacto(e.target.value)}
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
      {isError && <p className="text-red-700">Ocurrió un error al buscar retenciones.</p>}

      {data && data.items.length === 0 && (
        <p className="rounded border border-slate-200 bg-white p-6 text-center text-slate-600">
          Sin resultados para esta búsqueda.
        </p>
      )}

      {data && data.items.length > 0 && (
        <>
          <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="bg-slate-100 text-left">
                <tr>
                  <th className="px-3 py-2">Fecha</th>
                  <th className="px-3 py-2">Contacto</th>
                  <th className="px-3 py-2">Documento</th>
                  <th className="px-3 py-2 text-right">Importe</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data.items.map((r) => (
                  <tr key={r.idRetencion} className="hover:bg-slate-50">
                    <td className="px-3 py-2">{r.fecha ?? "—"}</td>
                    <td className="px-3 py-2">{r.contacto ?? "—"}</td>
                    <td className="px-3 py-2">
                      {r.documento ?? "—"} {r.numeroDocumento ?? ""}
                    </td>
                    <td className="px-3 py-2 text-right">
                      {r.importe != null ? r.importe.toLocaleString("es-AR") : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="flex items-center justify-between text-sm text-slate-600">
            <span>
              Página {data.page} de {totalPages} — {data.total} retenciones
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
